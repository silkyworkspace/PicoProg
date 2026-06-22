import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'picoprog.db')

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
c = conn.cursor()

c.executescript('''
CREATE TABLE IF NOT EXISTS notifications (
    id          INTEGER  PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER  NOT NULL,
    actor_id    INTEGER  NOT NULL,
    type        TEXT     NOT NULL,
    post_id     INTEGER  NOT NULL,
    is_read     INTEGER  NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY(user_id)  REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(actor_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(post_id)  REFERENCES posts(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
''')

conn.commit()
conn.close()
print("マイグレーション完了:", DB_PATH)
