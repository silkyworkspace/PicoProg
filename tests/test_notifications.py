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


class TestNotifications(unittest.TestCase):

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
        conn.execute('DELETE FROM favorites')
        conn.execute('DELETE FROM likes')
        conn.execute('DELETE FROM post_categories')
        conn.execute('DELETE FROM posts')
        conn.execute('DELETE FROM users')
        conn.commit()
        conn.close()
        self._register('alice', 'alice@example.com', 'Password1')
        self._register('bob', 'bob@example.com', 'Password1')

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

    def _create_post(self, email, content):
        self._login(email)
        self.client.post('/post/new', data={
            'content': content, 'categories': ['1']
        }, follow_redirects=True)
        self.client.get('/logout')
        with self.client.session_transaction() as sess:
            sess.clear()

    def _get_latest_post_id(self):
        conn = sqlite3.connect(TEST_DB_PATH)
        row = conn.execute('SELECT id FROM posts ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()
        return row[0] if row else None

    def _get_latest_notif_id(self, user_email):
        conn = sqlite3.connect(TEST_DB_PATH)
        row = conn.execute(
            'SELECT n.id FROM notifications n JOIN users u ON n.user_id = u.id WHERE u.email = ? ORDER BY n.id DESC LIMIT 1',
            (user_email,)
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def _is_read(self, notif_id):
        conn = sqlite3.connect(TEST_DB_PATH)
        row = conn.execute('SELECT is_read FROM notifications WHERE id = ?', (notif_id,)).fetchone()
        conn.close()
        return bool(row[0]) if row else False

    def test_notifications_requires_login(self):
        # 未ログインで /notifications → ログインページへリダイレクト
        response = self.client.get('/notifications')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_notifications_page_loads(self):
        # ログイン済みで /notifications にアクセスできる
        self._login('alice@example.com')
        response = self.client.get('/notifications')
        self.assertEqual(response.status_code, 200)

    def test_notification_appears_on_like(self):
        # 他人がいいねすると通知が表示される
        self._create_post('alice@example.com', 'Aliceの投稿')
        post_id = self._get_latest_post_id()
        self._login('bob@example.com')
        self.client.post(f'/post/{post_id}/like')
        self.client.get('/logout')
        with self.client.session_transaction() as sess:
            sess.clear()
        self._login('alice@example.com')
        response = self.client.get('/notifications')
        self.assertIn('bob', response.data.decode('utf-8'))

    def test_read_notification_marks_as_read(self):
        # 個別既読ルートにアクセスすると is_read が 1 になる
        self._create_post('alice@example.com', 'Aliceの投稿')
        post_id = self._get_latest_post_id()
        self._login('bob@example.com')
        self.client.post(f'/post/{post_id}/like')
        self.client.get('/logout')
        with self.client.session_transaction() as sess:
            sess.clear()
        notif_id = self._get_latest_notif_id('alice@example.com')
        self._login('alice@example.com')
        self.client.get(f'/notifications/{notif_id}/read', follow_redirects=True)
        self.assertTrue(self._is_read(notif_id))

    def test_read_other_users_notification_returns_404(self):
        # 他人の通知を既読にしようとすると404になる
        self._create_post('alice@example.com', 'Aliceの投稿')
        post_id = self._get_latest_post_id()
        self._login('bob@example.com')
        self.client.post(f'/post/{post_id}/like')
        self.client.get('/logout')
        with self.client.session_transaction() as sess:
            sess.clear()
        notif_id = self._get_latest_notif_id('alice@example.com')
        # bob が alice 宛の通知を既読にしようとする
        self._login('bob@example.com')
        response = self.client.get(f'/notifications/{notif_id}/read')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
