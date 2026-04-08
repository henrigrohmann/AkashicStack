import os
import sqlite3
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional

class AkashaEngine:
    def __init__(self, db_path: Optional[str] = None):
        # ルートディレクトリからの相対パス、またはHarmoniaから注入されたパスを使用
        if db_path is None:
            self.db_path = os.path.join(os.getcwd(), "data", "akasha.db")
        else:
            self.db_path = db_path
            
        self._ensure_directory()
        self._bootstrap()

    def _ensure_directory(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _bootstrap(self):
        """テーブル作成とジャーナル構造の初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    key TEXT PRIMARY KEY, 
                    content TEXT NOT NULL, 
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE TABLE IF NOT EXISTS traits (key TEXT, trait TEXT, PRIMARY KEY (key, trait))")
            conn.execute("CREATE TABLE IF NOT EXISTS sets (name TEXT PRIMARY KEY)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS set_items (
                    set_name TEXT, 
                    key TEXT, 
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                    PRIMARY KEY (set_name, key)
                )
            """)
            # ジャーナルをより「不沈」な構造へ強化
            conn.execute("""
                CREATE TABLE IF NOT EXISTS journals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    action TEXT NOT NULL, 
                    params TEXT, 
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _write_with_journal(self, action: str, params: Dict, sql_query: str, sql_params: tuple):
        """操作とログを単一のトランザクションで実行（アトミック性確保）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 1. 実際のデータ操作
                conn.execute(sql_query, sql_params)
                # 2. ジャーナルの記録
                conn.execute("INSERT INTO journals (action, params) VALUES (?, ?)", (action, json.dumps(params)))
                conn.commit()
        except sqlite3.Error as e:
            # ここで発生したエラーは上位（Harmonia等）に伝播させ、Master Logに記録させる
            raise e

    def commit(self, content: str) -> Dict:
        normalized = content.strip()
        key = hashlib.sha256(normalized.encode()).hexdigest()
        
        self._write_with_journal(
            "COMMIT", {"key": key},
            "INSERT OR IGNORE INTO chunks (key, content) VALUES (?, ?)", (key, normalized)
        )
        return {"key": key, "status": "committed"}

    def fetch(self, key: str) -> Dict:
        if not key or key == "None": return {"error": "key_required"}
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM chunks WHERE key = ?", (key,)).fetchone()
            if not row: return {"key": key, "error": "not_found"}
            traits = [r[0] for r in conn.execute("SELECT trait FROM traits WHERE key = ?", (key,)).fetchall()]
        return {"key": key, "content": row["content"], "created_at": row["created_at"], "traits": traits}

    def affix(self, key: str, trait: str) -> Dict:
        # 存在確認
        target = self.fetch(key)
        if "error" in target: return target
        
        self._write_with_journal(
            "AFFIX", {"key": key, "trait": trait},
            "INSERT OR IGNORE INTO traits (key, trait) VALUES (?, ?)", (key, trait)
        )
        return self.fetch(key)

    def create_set(self, name: str) -> Dict:
        self._write_with_journal(
            "SET_CREATE", {"name": name},
            "INSERT OR IGNORE INTO sets (name) VALUES (?)", (name,)
        )
        return {"status": "created", "name": name}

    def add_to_set(self, name: str, key: str) -> Dict:
        if not key or key == "None": return {"key": key, "error": "key_invalid"}
        
        # 集合の存在保証とアイテム追加をアトミックに行うために分離
        self.create_set(name)
        target = self.fetch(key)
        if "error" in target: return target
        
        self._write_with_journal(
            "SET_ADD", {"name": name, "key": key},
            "INSERT OR IGNORE INTO set_items (set_name, key) VALUES (?, ?)", (name, key)
        )
        return {"status": "added", "name": name, "key": key}

    def fetch_set(self, name: str, limit: int = 20) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            keys = [r[0] for r in conn.execute("SELECT key FROM set_items WHERE set_name = ? ORDER BY added_at DESC LIMIT ?", (name, limit)).fetchall()]
        return [self.fetch(k) for k in keys]

    def stream(self, limit: int = 20) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            keys = [r[0] for r in conn.execute("SELECT key FROM chunks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()]
        return [self.fetch(k) for k in keys]
