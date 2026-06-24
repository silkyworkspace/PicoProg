import sys
import os
import sqlite3
import unittest
import json

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


class TestLikes(unittest.TestCase):

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
        conn.execute('DELETE FROM likes')
        conn.execute('DELETE FROM favorites')
        conn.execute('DELETE FROM post_categories')
        conn.execute('DELETE FROM posts')
        conn.execute('DELETE FROM users')
        conn.commit()
        conn.close()
        # owner（投稿者）と other（操作する側）を用意する
        self._register_and_login('owner', 'owner@example.com', 'Password1')
        self._create_post()
        self.post_id = self._get_latest_post_id()
        self.client.get('/logout')
        self._register_and_login('other', 'other@example.com', 'Password1')

    def _register_and_login(self, username, email, password):
        self.client.post('/register', data={
            'username': username,
            'email': email,
            'password': password,
            'password_confirm': password
        }, follow_redirects=True)

    def _login(self, email, password='Password1'):
        self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def _create_post(self, content='テスト投稿です', categories=None):
        if categories is None:
            categories = ['1']
        self.client.post('/post/new', data={
            'content': content,
            'categories': categories
        }, follow_redirects=True)

    def _get_latest_post_id(self):
        conn = sqlite3.connect(TEST_DB_PATH)
        row = conn.execute('SELECT id FROM posts ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()
        return row[0] if row else None

    def _count_notifications(self, type_):
        conn = sqlite3.connect(TEST_DB_PATH)
        row = conn.execute(
            'SELECT COUNT(*) FROM notifications WHERE type = ?', (type_,)
        ).fetchone()
        conn.close()
        return row[0]

    # ===== いいねテスト =====

    def test_like_post(self):
        # 他人の投稿にいいね → liked: True, like_count: 1
        response = self.client.post(f'/post/{self.post_id}/like')
        data = json.loads(response.data)
        self.assertTrue(data['liked'])
        self.assertEqual(data['like_count'], 1)

    def test_unlike_post(self):
        # いいねを2回押す → toggle されて liked: False, like_count: 0
        self.client.post(f'/post/{self.post_id}/like')
        response = self.client.post(f'/post/{self.post_id}/like')
        data = json.loads(response.data)
        self.assertFalse(data['liked'])
        self.assertEqual(data['like_count'], 0)

    def test_like_requires_login(self):
        # 未ログインでいいね → ログインページへリダイレクト
        with self.client.session_transaction() as sess:
            sess.clear()
        response = self.client.post(f'/post/{self.post_id}/like')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_like_other_post_creates_notification(self):
        # 他人の投稿にいいね → like 通知が1件作られる
        self.client.post(f'/post/{self.post_id}/like')
        self.assertEqual(self._count_notifications('like'), 1)

    def test_like_own_post_no_notification(self):
        # 自分の投稿にいいね → 通知は作られない
        self.client.get('/logout')
        self._login('owner@example.com')
        self.client.post(f'/post/{self.post_id}/like')
        self.assertEqual(self._count_notifications('like'), 0)

    # ===== お気に入りテスト =====

    def test_favorite_post(self):
        # 他人の投稿をお気に入り → favorited: True, favorite_count: 1
        response = self.client.post(f'/post/{self.post_id}/favorite')
        data = json.loads(response.data)
        self.assertTrue(data['favorited'])
        self.assertEqual(data['favorite_count'], 1)

    def test_unfavorite_post(self):
        # お気に入りを2回押す → toggle されて favorited: False, favorite_count: 0
        self.client.post(f'/post/{self.post_id}/favorite')
        response = self.client.post(f'/post/{self.post_id}/favorite')
        data = json.loads(response.data)
        self.assertFalse(data['favorited'])
        self.assertEqual(data['favorite_count'], 0)

    def test_favorite_requires_login(self):
        # 未ログインでお気に入り → ログインページへリダイレクト
        with self.client.session_transaction() as sess:
            sess.clear()
        response = self.client.post(f'/post/{self.post_id}/favorite')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_favorite_other_post_creates_notification(self):
        # 他人の投稿をお気に入り → favorite 通知が1件作られる
        self.client.post(f'/post/{self.post_id}/favorite')
        self.assertEqual(self._count_notifications('favorite'), 1)

    def test_favorite_own_post_no_notification(self):
        # 自分の投稿をお気に入り → 通知は作られない
        self.client.get('/logout')
        self._login('owner@example.com')
        self.client.post(f'/post/{self.post_id}/favorite')
        self.assertEqual(self._count_notifications('favorite'), 0)


if __name__ == '__main__':
    unittest.main()
