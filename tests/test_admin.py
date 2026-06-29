import sys
import os
import sqlite3
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_picoprog.db')

from config import Config
Config.DB_PATH = TEST_DB_PATH

import app as flask_app


def _init_test_db():
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
            is_admin    INTEGER  NOT NULL DEFAULT 0,
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


class TestAdmin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _init_test_db()
        flask_app.app.config['TESTING'] = True
        flask_app.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = flask_app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def setUp(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.execute('DELETE FROM notifications')
        conn.execute('DELETE FROM post_categories')
        conn.execute('DELETE FROM posts')
        conn.execute('DELETE FROM users')
        conn.commit()
        conn.close()
        # 一般ユーザーと管理者を登録する
        self._register('user', 'user@example.com', 'Password1')
        self._register('admin', 'admin@example.com', 'Password1')
        self._set_admin('admin@example.com')

    def _register(self, username, email, password):
        self.client.post('/register', data={
            'username': username,
            'email': email,
            'password': password,
            'password_confirm': password
        }, follow_redirects=True)
        with self.client.session_transaction() as sess:
            sess.clear()

    def _login(self, email, password='Password1'):
        self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def _set_admin(self, email):
        """DBを直接更新してis_adminフラグを立てる"""
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.execute('UPDATE users SET is_admin = 1 WHERE email = ?', (email,))
        conn.commit()
        conn.close()

    def _create_post_as_user(self):
        """一般ユーザーでログインして投稿し、ログアウトする"""
        self._login('user@example.com')
        self.client.post('/post/new', data={
            'content': 'テスト投稿', 'categories': ['1']
        }, follow_redirects=True)
        self.client.get('/logout')

    def _get_user_id(self, email):
        conn = sqlite3.connect(TEST_DB_PATH)
        row = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        return row[0] if row else None

    def _get_latest_post_id(self):
        conn = sqlite3.connect(TEST_DB_PATH)
        row = conn.execute('SELECT id FROM posts ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()
        return row[0] if row else None

    # ===== アクセス制限テスト =====

    def test_admin_page_requires_login(self):
        # 未ログインで /admin → ログインページへリダイレクト
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_admin_page_rejects_normal_user(self):
        # 一般ユーザーで /admin → エラーになる
        self._login('user@example.com')
        response = self.client.get('/admin', follow_redirects=True)
        self.assertIn('管理者のみアクセスできます', response.data.decode('utf-8'))

    def test_admin_page_accessible_by_admin(self):
        # 管理者で /admin → 「管理者パネル」が表示される
        self._login('admin@example.com')
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 200)
        self.assertIn('管理者パネル', response.data.decode('utf-8'))

    # ===== ユーザー削除テスト =====

    def test_admin_can_delete_user(self):
        # 管理者が一般ユーザーを削除 → 成功する
        self._login('admin@example.com')
        user_id = self._get_user_id('user@example.com')
        response = self.client.post(
            f'/admin/user/{user_id}/delete', follow_redirects=True
        )
        self.assertIn('ユーザーを削除しました', response.data.decode('utf-8'))

    def test_admin_cannot_delete_self(self):
        # 管理者が自分自身を削除しようとする → エラーになる
        self._login('admin@example.com')
        admin_id = self._get_user_id('admin@example.com')
        response = self.client.post(
            f'/admin/user/{admin_id}/delete', follow_redirects=True
        )
        self.assertIn('自分自身を削除することはできません', response.data.decode('utf-8'))

    def test_normal_user_cannot_delete_user(self):
        # 一般ユーザーがユーザー削除を試みる → エラーになる
        self._login('user@example.com')
        admin_id = self._get_user_id('admin@example.com')
        response = self.client.post(
            f'/admin/user/{admin_id}/delete', follow_redirects=True
        )
        self.assertIn('管理者のみアクセスできます', response.data.decode('utf-8'))

    # ===== 投稿削除テスト =====

    def test_admin_can_delete_any_post(self):
        # 管理者が他人の投稿を削除 → 成功する
        self._create_post_as_user()
        post_id = self._get_latest_post_id()
        self._login('admin@example.com')
        response = self.client.post(
            f'/admin/post/{post_id}/delete', follow_redirects=True
        )
        self.assertIn('投稿を削除しました', response.data.decode('utf-8'))

    def test_normal_user_cannot_delete_via_admin(self):
        # 一般ユーザーが管理者ルートで投稿削除を試みる → エラーになる
        self._create_post_as_user()
        post_id = self._get_latest_post_id()
        self._login('user@example.com')
        response = self.client.post(
            f'/admin/post/{post_id}/delete', follow_redirects=True
        )
        self.assertIn('管理者のみアクセスできます', response.data.decode('utf-8'))

    # ===== 投稿検索テスト =====

    def _create_post_with_content(self, content):
        """一般ユーザーで指定内容の投稿を作成してログアウトする"""
        self._login('user@example.com')
        self.client.post('/post/new', data={
            'content': content, 'categories': ['1']
        }, follow_redirects=True)
        self.client.get('/logout')

    def test_admin_search_finds_matching_post(self):
        # キーワードに一致する投稿が検索結果に表示される
        self._create_post_with_content('Pythonの学習をしました')
        self._login('admin@example.com')
        response = self.client.get('/admin?q=Python')
        body = response.data.decode('utf-8')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Pythonの学習をしました', body)

    def test_admin_search_excludes_non_matching_post(self):
        # キーワードに一致しない投稿は検索結果に含まれない
        self._create_post_with_content('Flaskの復習をしました')
        self._login('admin@example.com')
        response = self.client.get('/admin?q=Python')
        body = response.data.decode('utf-8')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Flaskの復習をしました', body)

    def test_admin_search_returns_empty_when_no_match(self):
        # 一致しないキーワードで検索すると投稿が0件になる
        self._create_post_with_content('HTMLの練習をしました')
        self._login('admin@example.com')
        response = self.client.get('/admin?q=存在しないキーワード')
        body = response.data.decode('utf-8')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('HTMLの練習をしました', body)

    def test_admin_search_without_query_shows_posts(self):
        # キーワードなしで /admin にアクセスすると投稿一覧が表示される
        self._create_post_with_content('CSSの勉強をしました')
        self._login('admin@example.com')
        response = self.client.get('/admin')
        body = response.data.decode('utf-8')
        self.assertEqual(response.status_code, 200)
        self.assertIn('CSSの勉強をしました', body)


if __name__ == '__main__':
    unittest.main()
