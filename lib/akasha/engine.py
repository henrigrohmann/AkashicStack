import os
import sqlite3
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional

class AkashaEngine:
    def __init__(self, db_path: Optional[str] = None):
        # デフォルトパスをプロジェクトルート基準の絶対パスに解決
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.db_path = os.path.join(base_dir, "data", "akasha.db")
        else:
            self.db_path = os.path.abspath(db_path)

        self._ensure_directory()
        self._bootstrap()

    def _get_connection(self):
        """接続を取得し、外部キー制約などを有効化する共通メソッド"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _ensure_directory(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _bootstrap(self):
        """テーブル初期化。存在しない場合のみ作成。"""
        with self._get_connection() as conn:
            # chunksテーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    key TEXT PRIMARY KEY, 
                    content TEXT NOT NULL, 
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # traitsテーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traits (
                    key TEXT, 
                    trait TEXT, 
                    PRIMARY KEY (key, trait),
                    FOREIGN KEY (key) REFERENCES chunks(key) ON DELETE CASCADE
                )
            """)
            # setsテーブル
            conn.execute("CREATE TABLE IF NOT EXISTS sets (name TEXT PRIMARY KEY)")
            # set_itemsテーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS set_items (
                    set_name TEXT, 
                    key TEXT, 
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                    PRIMARY KEY (set_name, key),
                    FOREIGN KEY (set_name) REFERENCES sets(name) ON DELETE CASCADE,
                    FOREIGN KEY (key) REFERENCES chunks(key) ON DELETE CASCADE
                )
            """)
            # journalsテーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS journals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    action TEXT, 
                    params TEXT, 
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _log(self, action: str, params: Dict):
        with self._get_connection() as conn:
            conn.execute("INSERT INTO journals (action, params) VALUES (?, ?)", (action, json.dumps(params)))

    def commit(self, content: str) -> Dict:
        normalized = content.strip()
        key = hashlib.sha256(normalized.encode()).hexdigest()
        with self._get_connection() as conn:
            # ここでテーブルがないと OperationalError になるが、
            # __init__ で _bootstrap が成功していれば防げる
            conn.execute("INSERT OR IGNORE INTO chunks (key, content) VALUES (?, ?)", (key, normalized))
        self._log("COMMIT", {"key": key})
        return {"key": key, "status": "committed"}

    def fetch(self, key: str) -> Dict:
        if not key: return {"error": "key_required"}
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM chunks WHERE key = ?", (key,)).fetchone()
            if not row: return {"key": key, "error": "not_found"}
            
            cursor = conn.execute("SELECT trait FROM traits WHERE key = ?", (key,))
            traits = [r[0] for r in cursor.fetchall()]
            
        return {"key": key, "content": row["content"], "created_at": row["created_at"], "traits": traits}

    def affix(self, key: str, trait: str) -> Dict:
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO traits (key, trait) VALUES (?, ?)", (key, trait))
        self._log("AFFIX", {"key": key, "trait": trait})
        return self.fetch(key)

    def create_set(self, name: str) -> Dict:
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO sets (name) VALUES (?)", (name,))
        self._log("SET_CREATE", {"name": name})
        return {"status": "created", "name": name}

    def add_to_set(self, name: str, key: str) -> Dict:
        self.create_set(name) 
        target = self.fetch(key)
        if "error" in target: return target
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO set_items (set_name, key) VALUES (?, ?)", (name, key))
        self._log("SET_ADD", {"name": name, "key": key})
        return {"status": "added", "name": name, "key": key}

    def fetch_set(self, name: str, limit: int = 20) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT key FROM set_items WHERE set_name = ? ORDER BY added_at DESC LIMIT ?", 
                (name, limit)
            )
            keys = [r[0] for r in cursor.fetchall()]
        return [self.fetch(k) for k in keys]

    def stream(self, limit: int = 20) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT key FROM chunks ORDER BY created_at DESC LIMIT ?", 
                (limit,)
            )
            keys = [r[0] for r in cursor.fetchall()]
        return [self.fetch(k) for k in keys]
