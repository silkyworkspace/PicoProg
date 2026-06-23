import sys
import os
import sqlite3  # テスト用DBの作成・操作に使う
import unittest  # Python 標準のテスト用ライブラリ

# app.py があるディレクトリ（1つ上）を Python の検索パスに追加する
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テスト専用DBのパス（tests/ ディレクトリ内に作成される）
# 本番の database/picoprog.db には一切触らない
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_picoprog.db')

# get_db_connection() は Config.DB_PATH を参照してDBに接続する
# app を import する前に上書きしないと、本番DBに接続してしまう
from config import Config
Config.DB_PATH = TEST_DB_PATH

import app as flask_app  # Flaskアプリ本体をインポート


def _init_test_db():
    """テスト用DBを本番と同じテーブル構成で初期化する"""
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            username    TEXT     NOT NULL,
            email       TEXT     NOT NULL UNIQUE,
            password    TEXT     NOT NULL,
            profile     TEXT,
            icon_path   TEXT,
            created_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS posts (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER  NOT NULL,
            content     TEXT     NOT NULL,
            created_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            name        TEXT     NOT NULL UNIQUE,
            type        TEXT     NOT NULL,
            sort_order  INTEGER  NOT NULL DEFAULT 0,
            created_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS post_categories (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            post_id     INTEGER  NOT NULL,
            category_id INTEGER  NOT NULL,
            created_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY(post_id)     REFERENCES posts(id)      ON DELETE CASCADE,
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE,
            UNIQUE(post_id, category_id)
        );
        CREATE TABLE IF NOT EXISTS comments (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            post_id     INTEGER  NOT NULL,
            user_id     INTEGER  NOT NULL,
            content     TEXT     NOT NULL,
            created_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY(post_id)  REFERENCES posts(id)  ON DELETE CASCADE,
            FOREIGN KEY(user_id)  REFERENCES users(id)  ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS likes (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER  NOT NULL,
            post_id     INTEGER  NOT NULL,
            created_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY(user_id) REFERENCES users(id)  ON DELETE CASCADE,
            FOREIGN KEY(post_id) REFERENCES posts(id)  ON DELETE CASCADE,
            UNIQUE(user_id, post_id)
        );
        CREATE TABLE IF NOT EXISTS favorites (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER  NOT NULL,
            post_id     INTEGER  NOT NULL,
            created_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY(user_id) REFERENCES users(id)  ON DELETE CASCADE,
            FOREIGN KEY(post_id) REFERENCES posts(id)  ON DELETE CASCADE,
            UNIQUE(user_id, post_id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER  NOT NULL,
            actor_id    INTEGER  NOT NULL,
            type        TEXT     NOT NULL,
            post_id     INTEGER  NOT NULL,
            is_read     INTEGER  NOT NULL DEFAULT 0,
            read_at     DATETIME,
            created_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY(user_id)  REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(actor_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(post_id)  REFERENCES posts(id) ON DELETE CASCADE
        );
        INSERT OR IGNORE INTO categories (name, type, sort_order) VALUES
            ('学習中',                     'status', 1),
            ('制作中',                     'status', 2),
            ('完成・達成',                 'status', 3),
            ('Python基礎',                'tech',   4),
            ('Web開発(Flask)',             'tech',   5),
            ('データベース(SQL)',           'tech',   6),
            ('フロントエンド(HTML/CSS/JS)', 'tech',   7),
            ('その他',                     'tech',   8);
    ''')
    conn.commit()
    conn.close()


class TestAuth(unittest.TestCase):

    @classmethod
    def setUpClass(cls): # クラスメソッド: cls はこのクラス自身（TestAuth）を指す変数
        """全テストの前に1回だけ実行される"""
        _init_test_db()
        # Flaskをテストモードにする（エラーを例外として検知できるようになる）
        flask_app.app.config['TESTING'] = True
        # CSRFトークンの検証を無効化する（テストではトークンを生成できないため）
        flask_app.app.config['WTF_CSRF_ENABLED'] = False
        # ブラウザの代わりにHTTPリクエストを送るテストクライアントを作成する
        cls.client = flask_app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        """全テスト終了後に1回だけ実行される：テスト用DBを削除する"""
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def setUp(self): # 通常のメソッド: self = そのインスタンス（個々のオブジェクト）
        """各テストの前に毎回実行される：テストを互いに独立させるためのリセット処理"""
        # セッションをクリアして未ログイン状態にする
        # これをしないと前のテストのログイン状態が次のテストに引き継がれてしまう
        with self.client.session_transaction() as sess:
            sess.clear()
        # usersテーブルを空にして、テストユーザーが残らないようにする
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.execute('DELETE FROM users')
        conn.commit()
        conn.close()

    def _register(self, username='testuser', email='test@example.com', password='Password1'):
        """登録フォームにPOSTするヘルパー。成功するとそのままログイン状態になる。"""
        return self.client.post('/register', data={
            'username': username,
            'email': email,
            'password': password,
            'password_confirm': password
        }, follow_redirects=True)  # リダイレクト先のページまで自動で取得する

    def _login(self, email='test@example.com', password='Password1'):
        """ログインフォームにPOSTするヘルパー"""
        return self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)  # リダイレクト先のページまで自動で取得する

    # ===== 登録テスト =====

    def test_register_success(self):
        # 正常な情報で登録 → 「登録が完了しました」が表示されるはず
        response = self._register()
        self.assertEqual(response.status_code, 200)
        self.assertIn('登録が完了しました', response.data.decode('utf-8'))

    def test_register_duplicate_email(self):
        # 同じメールアドレスで2回登録 → 2回目は「すでに登録されています」エラーになるはず
        self._register()
        self.client.get('/logout')  # 登録後に自動ログインされるので一度ログアウトする
        response = self._register()  # 同じメールアドレスで再登録を試みる
        self.assertIn('すでに登録されています', response.data.decode('utf-8'))

    def test_register_password_mismatch(self):
        # パスワードと確認用パスワードが不一致 → 「パスワードが一致しません」エラーになるはず
        response = self.client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Password1',
            'password_confirm': 'Password2'  # ← 意図的に不一致にする
        }, follow_redirects=True)
        self.assertIn('パスワードが一致しません', response.data.decode('utf-8'))

    # ===== ログインテスト =====

    def test_login_success(self):
        # 登録済みユーザーが正しいパスワードでログイン → 「ログインしました」が表示されるはず
        self._register()
        self.client.get('/logout')  # 登録後に自動ログインされるので一度ログアウトする
        response = self._login()
        self.assertEqual(response.status_code, 200) # assertEqual(A, B) → A と B が 完全に一致するか確認
        self.assertIn('ログインしました', response.data.decode('utf-8')) # assertIn(A, B) → A が B の 中に含まれているか確認
        # 「ログインしました」という文字列が HTMLの中のどこかにあれば PASSED
        # なければ FAILED

    def test_login_wrong_password(self):
        # 間違ったパスワードでログイン → エラーメッセージが表示されるはず
        self._register()
        self.client.get('/logout')  # 登録後に自動ログインされるので一度ログアウトする
        response = self._login(password='WrongPass1')  # ← 意図的に間違ったパスワードを使う
        self.assertIn('メールアドレスまたはパスワードが間違っています', response.data.decode('utf-8'))

    def test_login_unknown_email(self):
        # 存在しないメールアドレスでログイン → エラーメッセージが表示されるはず
        response = self._login(email='nobody@example.com')  # ← DBに存在しないメール
        self.assertIn('メールアドレスまたはパスワードが間違っています', response.data.decode('utf-8'))

    # ===== ログアウトテスト =====

    def test_logout(self):
        # ログイン後にログアウト → 「ログアウトしました」が表示されるはず
        self._register()
        self._login()
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('ログアウトしました', response.data.decode('utf-8'))

    # ===== 未ログイン保護テスト =====

    def test_new_post_requires_login(self):
        # 未ログイン状態で投稿ページにアクセス → ログインページにリダイレクトされるはず
        # follow_redirects=False にすることでリダイレクト前の応答（302）を取得する
        with flask_app.app.test_client() as c:
            response = c.get('/post/new', follow_redirects=False)
            self.assertEqual(response.status_code, 302)   # 302 = リダイレクト（別ページに転送）
            self.assertIn('/login', response.location)    # 転送先がログインページであること


if __name__ == '__main__':
    unittest.main()
