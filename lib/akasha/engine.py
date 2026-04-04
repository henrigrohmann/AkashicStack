import os
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Optional

class AkashaEngine:
    def __init__(self, db_path: str = "data/akasha.db"):
        self.db_path = db_path
        # 1. 物理的なディレクトリの存在保証
        self._ensure_directory()
        # 2. データベースとテーブルの初期化
        self._bootstrap()

    def _ensure_directory(self):
        """データベースファイルが置かれるディレクトリを確実に作成する"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _bootstrap(self):
        """テーブル構造を初期化する（RDBの気配をここに閉じ込める）"""
        with sqlite3.connect(self.db_path) as conn:
            # Chunks: データの核（不変）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    key TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Traits: チャンクに付与されるインデックス（タグ）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traits (
                    key TEXT,
                    trait TEXT,
                    PRIMARY KEY (key, trait),
                    FOREIGN KEY (key) REFERENCES chunks(key)
                )
            """)
            conn.commit()

    def commit(self, content: str) -> Dict:
        """
        文章をハッシュ化して保存する。
        戻り値はJSONフレンドリーな辞書。
        """
        # ホワイトスペースの正規化（必要に応じて）
        normalized_content = content.strip()
        key = hashlib.sha256(normalized_content.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO chunks (key, content) VALUES (?, ?)",
                (key, normalized_content)
            )
            conn.commit()
        
        return {"key": key, "status": "committed"}

    def fetch(self, key: str) -> Dict:
        """
        特定のキーに紐づくデータを取得する。
        Traits（タグ）も結合して一つのオブジェクトとして返す。
        """
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
        """
        チャンクにTrait（タグ）を付与する。
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO traits (key, trait) VALUES (?, ?)",
                (key, trait)
            )
            conn.commit()
        
        # 付与後の最新状態を返す
        return self.fetch(key)

    def collect(self, traits: List[str]) -> List[Dict]:
        """
        指定されたTraitのいずれかを持つチャンクを全て取得する。
        """
        if not traits:
            return []

        placeholders = ', '.join(['?'] * len(traits))
        query = f"SELECT DISTINCT key FROM traits WHERE trait IN ({placeholders})"
        
        with sqlite3.connect(self.db_path) as conn:
            keys = [r[0] for r in conn.execute(query, traits).fetchall()]
            
        return [self.fetch(k) for k in keys]

    def stream(self, limit: int = 20) -> List[Dict]:
        """
        時系列（作成降順）でチャンクのリストを取得する。
        """
        with sqlite3.connect(self.db_path) as conn:
            keys = [r[0] for r in conn.execute(
                "SELECT key FROM chunks ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()]
            
        return [self.fetch(k) for k in keys]
