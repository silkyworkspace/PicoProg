import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'picoprog.db')

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
c = conn.cursor()

c.executescript('''
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

CREATE INDEX IF NOT EXISTS idx_users_email               ON users(email);
CREATE INDEX IF NOT EXISTS idx_posts_user_id             ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_created_at          ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_post_categories_post_id   ON post_categories(post_id);
CREATE INDEX IF NOT EXISTS idx_post_categories_cat_id    ON post_categories(category_id);
CREATE INDEX IF NOT EXISTS idx_comments_post_id          ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_favorites_user_id         ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_post_id         ON favorites(post_id);

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
print("データベースを初期化しました:", DB_PATH)
