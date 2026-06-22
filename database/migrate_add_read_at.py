import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'picoprog.db')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

try:
    c.execute("ALTER TABLE notifications ADD COLUMN read_at DATETIME")
    print("read_at カラムを追加しました")
except sqlite3.OperationalError:
    print("read_at カラムはすでに存在します（スキップ）")

conn.commit()
conn.close()
print("マイグレーション完了:", DB_PATH)
