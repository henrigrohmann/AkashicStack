import sqlite3
import json
import hashlib
from datetime import datetime
import os

class AkashaEngine:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        # Cortex/Hippocampus共通: Atom管理
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                key TEXT PRIMARY KEY, content TEXT, created_at TEXT
            )""")
        self.conn.execute("CREATE TABLE IF NOT EXISTS traits (key TEXT, trait TEXT)")
        # Nucleus専用: システム設定・認証
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nucleus (
                category TEXT, identifier TEXT, data TEXT,
                PRIMARY KEY(category, identifier)
            )""")
        self.conn.commit()

    # --- 大脳皮質(Cortex) / 短期記憶(Hippocampus) 共通操作 ---
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
        cursor = self.conn.execute("SELECT 1 FROM traits WHERE key = ? AND trait = ?", (key, trait))
        if not cursor.fetchone():
            self.conn.execute("INSERT INTO traits VALUES (?, ?)", (key, trait))
            self.conn.commit()
        return {"status": "affixed", "key": key, "trait": trait}

    # --- Nucleus(中枢金庫) 専用操作 ---
    def vault_store(self, category, identifier, data):
        self.conn.execute("INSERT OR REPLACE INTO nucleus VALUES (?, ?, ?)", (category, identifier, json.dumps(data)))
        self.conn.commit()

    def vault_retrieve(self, category, identifier):
        cursor = self.conn.execute("SELECT data FROM nucleus WHERE category = ? AND identifier = ?", (category, identifier))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
