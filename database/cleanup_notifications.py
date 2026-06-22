import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'picoprog.db')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute('''
    DELETE FROM notifications
    WHERE is_read = 1
    AND read_at <= datetime('now', '-30 days', 'localtime')
''')

deleted = c.rowcount
conn.commit()
conn.close()
print(f"削除完了: {deleted} 件（既読から30日経過）")
