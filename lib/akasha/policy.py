class AkashaRole:
    ADMIN = "admin"      # 全操作可能（CLI/Master用）
    CELL = "cell"        # 自身のデータのみ操作可能（会員用）
    LEAF = "leaf"        # 読み取り専用（ゲスト用）

# ロールごとの許可メソッド
POLICY_MAP = {
    AkashaRole.ADMIN: ["write", "read", "list", "affix", "set", "help", "initialize", "admin_stats"],
    AkashaRole.CELL:  ["write", "read", "list", "affix", "set", "help", "initialize"],
    AkashaRole.LEAF:  ["read", "list", "help", "initialize"]
}

def is_authorized(role: str, method: str) -> bool:
    return method in POLICY_MAP.get(role, [])
