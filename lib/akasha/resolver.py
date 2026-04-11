class ContextResolver:
    @staticmethod
    def resolve(session, params, history=None):
        """
        指示詞を解決し、実体（Atom）のキーを返す。
        history: api/main.py から渡される [key0, key1, ...] のリスト
        """
        target = params.get("id") or params.get("key")
        
        # ターゲットが空、または $it の場合は直近のキーを返す
        if not target or target == "$it":
            return session.it_key
            
        # シリアル番号 ($0, $1...) の解決
        if str(target).startswith("$"):
            try:
                # $ の後ろの数字を取得
                idx = int(target[1:])
                
                # api/main.py が管理している履歴キャッシュがあればそこから引く
                if history is not None and 0 <= idx < len(history):
                    return history[idx]
                
                # 履歴がない、あるいは範囲外の場合はそのまま返す
                return target
            except (ValueError, IndexError):
                return target
                
        # 指示詞でない場合はそのまま（UUIDなど）
        return target
