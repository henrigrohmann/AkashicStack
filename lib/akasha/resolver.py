class ContextResolver:
    @staticmethod
    def resolve(session, params):
        target = params.get("id")
        # $it 解決
        if target == "$it" or not target:
            return session.it_key
        # シリアル番号 ($0, $1...) 解決
        if str(target).startswith("$"):
            try:
                idx = int(target[1:])
                # ここでは簡易的に直近のstreamから引く想定
                history = session.engine.stream(limit=20)
                return history[idx]["key"] if 0 <= idx < len(history) else target
            except: return target
        return target
