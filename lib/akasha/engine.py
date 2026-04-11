import sqlite3
import json
import hashlib
from datetime import datetime
import os

class AkashaEngine:
    def __init__(self, db_path="data/akasha.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                key TEXT PRIMARY KEY,
                content TEXT,
                created_at TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS traits (
                key TEXT,
                trait TEXT,
                FOREIGN KEY(key) REFERENCES chunks(key)
            )
        """)
        self.conn.commit()

    def commit(self, content: str):
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        key = hashlib.sha256(content.encode()).hexdigest()
        try:
            self.conn.execute(
                "INSERT INTO chunks (key, content, created_at) VALUES (?, ?, ?)",
                (key, content, created_at)
            )
            self.conn.commit()
            return {"status": "committed", "key": key}
        except sqlite3.IntegrityError:
            return {"status": "exists", "key": key}

    def stream(self, limit=10):
        cursor = self.conn.execute(
            "SELECT key, content, created_at FROM chunks ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            key = row[0]
            t_cursor = self.conn.execute("SELECT trait FROM traits WHERE key = ?", (key,))
            traits = [t[0] for t in t_cursor.fetchall()]
            results.append({
                "key": key,
                "content": row[1],
                "created_at": row[2],
                "traits": traits
            })
        return results

    def affix(self, key: str, trait: str):
        cursor = self.conn.execute(
            "SELECT 1 FROM traits WHERE key = ? AND trait = ?", (key, trait)
        )
        if not cursor.fetchone():
            self.conn.execute(
                "INSERT INTO traits (key, trait) VALUES (?, ?)", (key, trait)
            )
            self.conn.commit()
        return {"status": "affixed", "key": key, "trait": trait}

    def remove_trait(self, key: str, trait: str):
        self.conn.execute("DELETE FROM traits WHERE key = ? AND trait = ?", (key, trait))
        self.conn.commit()
        return {"status": "success", "key": key, "removed_trait": trait}

    def find_by_trait(self, trait: str):
        cursor = self.conn.execute("""
            SELECT c.key, c.content, c.created_at 
            FROM chunks c 
            JOIN traits t ON c.key = t.key 
            WHERE t.trait = ?
        """, (trait,))
        return [{"key": r[0], "content": r[1], "created_at": r[2]} for r in cursor.fetchall()]

    def add_to_set(self, set_name: str, key: str):
        return self.affix(key, f"set:{set_name}")

    def list_sets(self):
        cursor = self.conn.execute("SELECT DISTINCT trait FROM traits WHERE trait LIKE 'set:%'")
        return [{"set_name": row[0].replace("set:", "")} for row in cursor.fetchall()]

    def get_set_members(self, set_name: str):
        return self.find_by_trait(f"set:{set_name}")

    def delete_atom(self, key: str):
        self.conn.execute("DELETE FROM chunks WHERE key = ?", (key,))
        self.conn.execute("DELETE FROM traits WHERE key = ?", (key,))
        self.conn.commit()
        return {"status": "deleted", "key": key}
