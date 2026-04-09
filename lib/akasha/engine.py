import sqlite3
import json
import hashlib
from datetime import datetime
import os

class AkashaEngine:
    def __init__(self, db_path="data/akasha.db"):
        # ディレクトリの存在を保証
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        # Chunks: Atom本体の保存
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                key TEXT PRIMARY KEY,
                content TEXT,
                created_at TEXT
            )
        """)
        # Traits: 属性・タグ・集合情報の保存
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS traits (
                key TEXT,
                trait TEXT,
                FOREIGN KEY(key) REFERENCES chunks(key)
            )
        """)
        self.conn.commit()

    # --- 基本操作: Write / Read / Stream ---
    def commit(self, content: str):
        """Atomを書き込み、SHA-256のKeyを返す"""
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
        """最近のAtomを一覧表示（Trait情報も結合）"""
        cursor = self.conn.execute(
            "SELECT key, content, created_at FROM chunks ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            key = row[0]
            # 各Atomに紐づくTraitを取得
            t_cursor = self.conn.execute("SELECT trait FROM traits WHERE key = ?", (key,))
            traits = [t[0] for t in t_cursor.fetchall()]
            results.append({
                "key": key,
                "content": row[1],
                "created_at": row[2],
                "traits": traits
            })
        return results

    # --- Trait (属性) 操作 ---
    def affix(self, key: str, trait: str):
        """Atomに属性(Trait)を付与する"""
        # 重複登録を防ぐ
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
        """特定のAtomから指定した属性を削除する"""
        self.conn.execute(
            "DELETE FROM traits WHERE key = ? AND trait = ?",
            (key, trait)
        )
        self.conn.commit()
        return {"status": "success", "key": key, "removed_trait": trait}

    def find_by_trait(self, trait: str):
        """属性を指定してAtomを検索する"""
        cursor = self.conn.execute(
            """
            SELECT c.key, c.content, c.created_at 
            FROM chunks c 
            JOIN traits t ON c.key = t.key 
            WHERE t.trait = ?
            """, (trait,)
        )
        return [{"key": r[0], "content": r[1], "created_at": r[2]} for r in cursor.fetchall()]

    # --- Set (集合) 操作 ---
    def add_to_set(self, set_name: str, key: str):
        """Atomを集合(Set)に登録する。内部的には 'set:{name}' というTraitとして扱う"""
        return self.affix(key, f"set:{set_name}")

    def list_sets(self):
        """存在する集合(Set)の一覧をプレフィックスなしで取得する"""
        cursor = self.conn.execute(
            "SELECT DISTINCT trait FROM traits WHERE trait LIKE 'set:%'"
        )
        return [{"set_name": row[0].replace("set:", "")} for row in cursor.fetchall()]

    def get_set_members(self, set_name: str):
        """特定の集合に属するAtom一覧を返す"""
        return self.find_by_trait(f"set:{set_name}")

    # --- 削除操作 ---
    def delete_atom(self, key: str):
        """Atom本体とその属性情報を完全に削除する"""
        self.conn.execute("DELETE FROM chunks WHERE key = ?", (key,))
        self.conn.execute("DELETE FROM traits WHERE key = ?", (key,))
        self.conn.commit()
        return {"status": "deleted", "key": key}
