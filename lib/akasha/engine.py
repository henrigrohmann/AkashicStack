import os
import sqlite3
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional

class AkashaEngine:
    def __init__(self, db_path: str = "data/akasha.db"):
        self.db_path = db_path
        self._ensure_directory()
        self._bootstrap()

    def _ensure_directory(self):
        """DBディレクトリの作成"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _bootstrap(self):
        """テーブル構造の初期化"""
        with sqlite3.connect(self.db_path) as conn:
            # Chunks: データ本体
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    key TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Traits: 特性(タグ)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traits (
                    key TEXT,
                    trait TEXT,
                    PRIMARY KEY (key, trait),
                    FOREIGN KEY (key) REFERENCES chunks(key)
                )
            """)
            # Sets: 集合
            conn.execute("CREATE TABLE IF NOT EXISTS sets (name TEXT PRIMARY KEY)")
            # Set_Items: 集合とChunkの紐付け
            conn.execute("""
                CREATE TABLE IF NOT EXISTS set_items (
                    set_name TEXT,
                    key TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (set_name, key)
                )
            """)
            # Journals: 操作ログ
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
        """ジャーナルへの記録"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO journals (action, params) VALUES (?, ?)",
                (action, json.dumps(params))
            )
            conn.commit()

    def commit(self, content: str) -> Dict:
        """文章の保存"""
        normalized = content.strip()
        key = hashlib.sha256(normalized.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO chunks (key, content) VALUES (?, ?)",
                (key, normalized)
            )
            conn.commit()
        self._log("COMMIT", {"key": key})
        return {"key": key, "status": "committed"}

    def fetch(self, key: str) -> Dict:
        """データの取得"""
        if not key or key == "None":
            return {"error": "key_required"}
            
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM chunks WHERE key = ?", (key,)).fetchone()
            if not row:
                return {"key": key, "error": "not_found"}
            
            traits = [r[0] for r in conn.execute(
                "SELECT trait FROM traits WHERE key = ?", (key,)
            ).fetchall()]
            
        return {
            "key": key,
            "content": row["content"],
            "created_at": row["created_at"],
            "traits": traits
        }

    def affix(self, key: str, trait: str) -> Dict:
        """特性の付与"""
        target = self.fetch(key)
        if "error" in target: return target

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO traits (key, trait) VALUES (?, ?)",
                (key, trait)
            )
            conn.commit()
        self._log("AFFIX", {"key": key, "trait": trait})
        return self.fetch(key)

    def create_set(self, name: str) -> Dict:
        """集合の作成"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO sets (name) VALUES (?)", (name,))
            conn.commit()
        self._log("SET_CREATE", {"name": name})
        return {"status": "created", "name": name}

    def add_to_set(self, name: str, key: str) -> Dict:
        """集合への追加"""
        if not key or key == "None":
            return {"key": key, "error": "key_required"}

        self.create_set(name) # 存在保証
        target = self.fetch(key)
        if "error" in target: return target

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO set_items (set_name, key) VALUES (?, ?)",
                (name, key)
            )
            conn.commit()
        self._log("SET_ADD", {"name": name, "key": key})
        return {"status": "added", "name": name, "key": key}

    def fetch_set(self, name: str, limit: int = 20) -> List[Dict]:
        """集合内の取得"""
        with sqlite3.connect(self.db_path) as conn:
            keys = [r[0] for r in conn.execute(
                "SELECT key FROM set_items WHERE set_name = ? ORDER BY added_at DESC LIMIT ?",
                (name, limit)
            ).fetchall()]
        return [self.fetch(k) for k in keys]

    def stream(self, limit: int = 20) -> List[Dict]:
        """直近のストリーム"""
        with sqlite3.connect(self.db_path) as conn:
            keys = [r[0] for r in conn.execute(
                "SELECT key FROM chunks ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()]
        return [self.fetch(k) for k in keys]
