import sqlite3
import json
import hashlib
from datetime import datetime

class AkashaEngine:
    def __init__(self, db_path: str = "data/akasha.db"):
        self.db_path = db_path
        
        # ディレクトリが存在しない場合
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        self._bootstrap()

    def _bootstrap(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    uid TEXT PRIMARY KEY,       -- ULID等
                    hash TEXT UNIQUE,           -- Content Hash
                    body TEXT,                  -- 本文
                    meta TEXT,                  -- JSON (tags, summary等)
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON chunks(hash)")

    def put(self, body: str, meta: dict, uid: str) -> str:
        content_hash = hashlib.sha256(body.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    "INSERT INTO chunks (uid, hash, body, meta) VALUES (?, ?, ?, ?)",
                    (uid, content_hash, body, json.dumps(meta, ensure_ascii=False))
                )
            except sqlite3.IntegrityError:
                pass # 同一ハッシュは既存優先
        return content_hash

