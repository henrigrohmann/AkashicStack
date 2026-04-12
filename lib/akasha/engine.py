import sqlite3
import json
import hashlib
from datetime import datetime
import os

class AkashaEngine:
    """大脳皮質(Cortex)・短期記憶(Hippocampus)用の汎用エンジン"""
    def __init__(self, db_path, is_volatile=False):
        self.is_volatile = is_volatile
        if is_volatile and os.path.exists(db_path):
            os.remove(db_path)  # 短期記憶は起動時にリセット
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                key TEXT PRIMARY KEY, content TEXT, created_at TEXT
            )""")
        self.conn.execute("CREATE TABLE IF NOT EXISTS traits (key TEXT, trait TEXT)")
        self.conn.commit()

    def commit(self, content: str):
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        key = hashlib.sha256(content.encode()).hexdigest()
        try:
            self.conn.execute("INSERT INTO chunks VALUES (?, ?, ?)", (key, content, created_at))
            self.conn.commit()
            return {"status": "committed", "key": key}
        except sqlite3.IntegrityError:
            return {"status": "exists", "key": key}

    def stream(self, limit=10):
        cursor = self.conn.execute("SELECT key, content, created_at FROM chunks ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        results = []
        for row in rows:
            t_cursor = self.conn.execute("SELECT trait FROM traits WHERE key = ?", (row[0],))
            traits = [t[0] for t in t_cursor.fetchall()]
            results.append({"key": row[0], "content": row[1], "created_at": row[2], "traits": traits})
        return results

    def affix(self, key: str, trait: str):
        self.conn.execute("INSERT OR IGNORE INTO traits VALUES (?, ?)", (key, trait))
        self.conn.commit()
        return {"status": "affixed", "key": key, "trait": trait}

class NucleusEngine(AkashaEngine):
    """中枢金庫(Nucleus)専用エンジン：汎用メソッドを制限し、金庫操作を追加"""
    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nucleus (
                category TEXT, identifier TEXT, data TEXT,
                PRIMARY KEY(category, identifier)
            )""")
        self.conn.commit()

    def commit(self, content): raise PermissionError("Nucleus does not support generic commit.")
    def stream(self, limit): raise PermissionError("Nucleus does not support generic stream.")

    def vault_store(self, category, identifier, data):
        self.conn.execute("INSERT OR REPLACE INTO nucleus VALUES (?, ?, ?)", (category, identifier, json.dumps(data)))
        self.conn.commit()

    def vault_retrieve(self, category, identifier):
        cursor = self.conn.execute("SELECT data FROM nucleus WHERE category = ? AND identifier = ?", (category, identifier))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
