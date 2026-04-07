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
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _bootstrap(self):
        """テーブル構造の初期化。集合(Sets)と操作ログ(Journals)を追加。"""
        with sqlite3.connect(self.db_path) as conn:
            # Chunks: データの核
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    key TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Traits: 特性（タグ）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traits (
                    key TEXT,
                    trait TEXT,
                    PRIMARY KEY (key, trait),
                    FOREIGN KEY (key) REFERENCES chunks(key)
                )
            """)
            # Sets: 集合（器）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sets (
                    name TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Set_Items: 集合とChunkの紐付け
            conn.execute("""
                CREATE TABLE IF NOT EXISTS set_items (
                    set_name TEXT,
                    key TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (set_name, key),
                    FOREIGN KEY (set_name) REFERENCES sets(name),
                    FOREIGN KEY (key) REFERENCES chunks(key)
                )
            """)
            # Journals: 操作履歴（ロールバック用）
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
        """操作ログをDBに記録"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO journals (action, params) VALUES (?, ?)",
                (action, json.dumps(params))
            )
            conn.commit()

    def commit(self, content: str) -> Dict:
        normalized_content = content.strip()
        key = hashlib.sha256(normalized_content.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO chunks (key, content) VALUES (?, ?)",
                (key, normalized_content)
            )
            conn.commit()
        
        self._log("COMMIT", {"key": key, "content_preview": normalized_content[:20]})
        return {"key": key, "status": "committed"}

    def fetch(self, key: str) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT content, created_at FROM chunks WHERE key = ?", (key,)
            ).fetchone()
            
            if not row:
                return {"key": key, "error": "not_found"}
            
            traits_rows = conn.execute(
                "SELECT trait FROM traits WHERE key = ?", (key,)
            ).fetchall()
            traits = [r["trait"] for r in traits_rows]
            
        return {
            "key": key,
            "content": row["content"],
            "created_at": row["created_at"],
            "traits": traits
        }

    def affix(self, key: str, trait: str) -> Dict:
        # キーの存在確認
        target = self.fetch(key)
        if "error" in target:
            return target

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO traits (key, trait) VALUES (?, ?)",
                (key, trait)
            )
            conn.commit()
        
        self._log("AFFIX", {"key": key, "trait": trait})
        return self.fetch(key)

    # --- 集合(Set)操作の実装 ---

    def create_set(self, name: str) -> Dict:
        """新しい集合(器)を作成する"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO sets (name) VALUES (?)", (name,))
            conn.commit()
        self._log("SET_CREATE", {"name": name})
        return {"status": "created", "name": name}

    def add_to_set(self, name: str, key: str) -> Dict:
        """集合にChunkを追加する。集合がなければ自動作成。"""
        # 集合の存在を保証
        self.create_set(name)
        # キーの存在確認
        target = self.fetch(key)
        if "error" in target:
            return target

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO set_items (set_name, key) VALUES (?, ?)",
                (name, key)
            )
            conn.commit()
        
        self._log("SET_ADD", {"name": name, "key": key})
        return {"status": "added", "name": name, "key": key}

    def fetch_set(self, name: str, limit: int = 20) -> List[Dict]:
        """集合内のChunkを指定されたリミット分、降順で取得"""
        with sqlite3.connect(self.db_path) as conn:
            keys = [r[0] for r in conn.execute(
                "SELECT key FROM set_items WHERE set_name = ? ORDER BY added_at DESC LIMIT ?",
                (name, limit)
            ).fetchall()]
            
        return [self.fetch(k) for k in keys]

    # --- ユーティリティ ---

    def collect(self, traits: List[str]) -> List[Dict]:
        if not traits: return []
        placeholders = ', '.join(['?'] * len(traits))
        query = f"SELECT DISTINCT key FROM traits WHERE trait IN ({placeholders})"
        with sqlite3.connect(self.db_path) as conn:
            keys = [r[0] for r in conn.execute(query, traits).fetchall()]
        return [self.fetch(k) for k in keys]

    def stream(self, limit: int = 20) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            keys = [r[0] for r in conn.execute(
                "SELECT key FROM chunks ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()]
        return [self.fetch(k) for k in keys]
