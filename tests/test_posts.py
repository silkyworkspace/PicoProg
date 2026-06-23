import sys
import os
import sqlite3
import unittest

# app.py があるディレクトリ（1つ上）を Python の検索パスに追加する
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# test_auth.py と同じテスト専用DBを使う
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_picoprog.db')

# app を import する前に Config.DB_PATH を上書きする
from config import Config
Config.DB_PATH = TEST_DB_PATH

import app as flask_app


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


class TestPosts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """全テストの前に1回だけ実行される"""
        _init_test_db()
        flask_app.app.config['TESTING'] = True
        flask_app.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = flask_app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        """全テスト終了後に1回だけ実行される：テスト用DBを削除する"""
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def setUp(self):
        """各テストの前に毎回実行される：DBとセッションをリセットする"""
        # セッションをクリアして未ログイン状態にする
        with self.client.session_transaction() as sess:
            sess.clear()
        # users・posts・comments テーブルを空にする
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.execute('DELETE FROM comments')
        conn.execute('DELETE FROM post_categories')
        conn.execute('DELETE FROM posts')
        conn.execute('DELETE FROM users')
        conn.commit()
        conn.close()
        # テストユーザーを登録してログインした状態にしておく
        self._register_and_login('owner', 'owner@example.com', 'Password1')

    def _register_and_login(self, username, email, password):
        """ユーザーを登録してそのままログインするヘルパー"""
        self.client.post('/register', data={
            'username': username,
            'email': email,
            'password': password,
            'password_confirm': password
        }, follow_redirects=True)

    def _login(self, email, password='Password1'):
        """ログインするヘルパー"""
        self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def _create_post(self, content='テスト投稿です', categories=None):
        """投稿を作成するヘルパー。categories はカテゴリIDのリスト。"""
        if categories is None:
            categories = ['1']  # デフォルトは「学習中」
        return self.client.post('/post/new', data={
            'content': content,
            'categories': categories
        }, follow_redirects=True)

    def _get_latest_post_id(self):
        """DBから最新の投稿IDを取得するヘルパー"""
        conn = sqlite3.connect(TEST_DB_PATH)
        row = conn.execute('SELECT id FROM posts ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()
        return row[0] if row else None

    def _get_latest_comment_id(self):
        """DBから最新のコメントIDを取得するヘルパー"""
        conn = sqlite3.connect(TEST_DB_PATH)
        row = conn.execute('SELECT id FROM comments ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()
        return row[0] if row else None

    # ===== 投稿作成テスト =====

    def test_create_post_success(self):
        # 正常な内容とカテゴリで投稿 → 「投稿しました」が表示されるはず
        response = self._create_post()
        self.assertIn('投稿しました', response.data.decode('utf-8'))

    def test_create_post_no_content(self):
        # 内容が空で投稿 → エラーになるはず
        response = self._create_post(content='')
        self.assertIn('投稿内容を入力してください', response.data.decode('utf-8'))

    def test_create_post_no_category(self):
        # カテゴリを選ばずに投稿 → エラーになるはず
        response = self.client.post('/post/new', data={
            'content': 'カテゴリなし投稿',
            # categories を送らない
        }, follow_redirects=True)
        self.assertIn('カテゴリを1つ以上選択してください', response.data.decode('utf-8'))

    # ===== 投稿編集テスト =====

    def test_edit_own_post(self):
        # 自分の投稿を編集 → 成功するはず
        self._create_post()
        post_id = self._get_latest_post_id()
        response = self.client.post(f'/post/{post_id}/edit', data={
            'content': '編集後の内容',
            'categories': ['2']
        }, follow_redirects=True)
        self.assertIn('投稿を更新しました', response.data.decode('utf-8'))

    def test_edit_other_post(self):
        # 他のユーザーの投稿を編集しようとする → エラーになるはず
        self._create_post()                          # owner が投稿
        post_id = self._get_latest_post_id()

        self.client.get('/logout')                   # owner をログアウト
        self._register_and_login('other', 'other@example.com', 'Password1')  # 別ユーザーでログイン

        response = self.client.post(f'/post/{post_id}/edit', data={
            'content': '不正に編集',
            'categories': ['1']
        }, follow_redirects=True)
        self.assertIn('他のユーザーの投稿は編集できません', response.data.decode('utf-8'))

    # ===== 投稿削除テスト =====

    def test_delete_own_post(self):
        # 自分の投稿を削除 → 成功するはず
        self._create_post()
        post_id = self._get_latest_post_id()
        response = self.client.post(f'/post/{post_id}/delete', follow_redirects=True)
        self.assertIn('投稿を削除しました', response.data.decode('utf-8'))

    def test_delete_other_post(self):
        # 他のユーザーの投稿を削除しようとする → エラーになるはず
        self._create_post()                          # owner が投稿
        post_id = self._get_latest_post_id()

        self.client.get('/logout')                   # owner をログアウト
        self._register_and_login('other', 'other@example.com', 'Password1')  # 別ユーザーでログイン

        response = self.client.post(f'/post/{post_id}/delete', follow_redirects=True)
        self.assertIn('他のユーザーの投稿は削除できません', response.data.decode('utf-8'))

    # ===== コメントテスト =====

    def test_create_comment_success(self):
        # 投稿にコメント → 「コメントしました」が表示されるはず
        self._create_post()
        post_id = self._get_latest_post_id()
        response = self.client.post(f'/post/{post_id}/comment', data={
            'content': 'テストコメントです'
        }, follow_redirects=True)
        self.assertIn('コメントしました', response.data.decode('utf-8'))

    def test_delete_own_comment(self):
        # 自分のコメントを削除 → 成功するはず
        self._create_post()
        post_id = self._get_latest_post_id()
        self.client.post(f'/post/{post_id}/comment', data={
            'content': '削除するコメント'
        }, follow_redirects=True)
        comment_id = self._get_latest_comment_id()
        response = self.client.post(f'/comment/{comment_id}/delete', follow_redirects=True)
        self.assertIn('コメントを削除しました', response.data.decode('utf-8'))

    def test_delete_other_comment(self):
        # 他のユーザーのコメントを削除しようとする → エラーになるはず
        self._create_post()
        post_id = self._get_latest_post_id()
        self.client.post(f'/post/{post_id}/comment', data={
            'content': 'ownerのコメント'
        }, follow_redirects=True)
        comment_id = self._get_latest_comment_id()

        self.client.get('/logout')                   # owner をログアウト
        self._register_and_login('other', 'other@example.com', 'Password1')  # 別ユーザーでログイン

        response = self.client.post(f'/comment/{comment_id}/delete', follow_redirects=True)
        self.assertIn('他のユーザーのコメントは削除できません', response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
