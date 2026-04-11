import sys
import json
import argparse
import threading
from lib.akasha.manager import AkashaManager
from lib.akasha.resolver import ContextResolver

class AkashaCore:
    """
    Akashaの全インターフェース（CLI, Flet, MCP）の背後で動く統合司令塔。
    """
    def __init__(self, mode="seeds"):
        # seedsかenterpriseかで挙動を切り替えるマネージャー
        self.manager = AkashaManager(is_enterprise=(mode == "enterprise"))
        # セッションごとの直近キー履歴（$0, $1...用）
        self.history_cache = {} # {client_id: [key_history]}

    def dispatch(self, json_rpc_req):
        """
        JSON-RPC 2.0形式の入力を受け取り、処理結果を返す。
        """
        try:
            req = json.loads(json_rpc_req) if isinstance(json_rpc_req, str) else json_rpc_req
            method = req.get("method")
            params = req.get("params", {})
            client_id = params.get("client_id", "me")
            req_id = req.get("id")

            session = self.manager.get_session(client_id)
            
            # --- メソッド・ルーティング ---
            if method == "write":
                res = session.engine.commit(params.get("text", ""))
                session.it_key = res.get("key")
                # 履歴キャッシュを更新
                self._update_history(client_id, res.get("key"))
                
                # Enterpriseモードなら共有BBSへミラーリング
                if self.manager.is_enterprise:
                    self.manager.shared_queue.put({"content": f"[{client_id}] {params.get('text')}"})
                
                return self._format_response(res, req_id)

            elif method == "read":
                # 指示詞解決レイヤー（$it, $0 等）
                resolved_id = ContextResolver.resolve(session, params, self.history_cache.get(client_id, []))
                # 全アトムから該当を検索（将来的にengine側で最適化）
                atoms = session.engine.stream(limit=1000)
                result = next((a for a in atoms if a['key'] == resolved_id), {"error": "not_found"})
                return self._format_response(result, req_id)

            elif method == "list":
                limit = params.get("limit", 10)
                res = session.engine.stream(limit=limit)
                return self._format_response(res, req_id)

            else:
                return self._format_error(-32601, f"Method '{method}' not found", req_id)

        except Exception as e:
            return self._format_error(-32603, str(e))

    def _update_history(self, client_id, key):
        if client_id not in self.history_cache:
            self.history_cache[client_id] = []
        self.history_cache[client_id].insert(0, key)
        # 直近20件のみ保持
        self.history_cache[client_id] = self.history_cache[client_id][:20]

    def _format_response(self, result, req_id):
        return {"jsonrpc": "2.0", "result": result, "id": req_id}

    def _format_error(self, code, message, req_id=None):
        return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": req_id}

# --- 実行エントリーポイント ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Akasha Unified API Server")
    parser.add_argument("--mode", default="seeds", choices=["seeds", "enterprise"])
    parser.add_argument("--stdio", action="store_true", help="Enable MCP/CLI stdio mode")
    args = parser.parse_args()

    core = AkashaCore(mode=args.mode)

    if args.stdio:
        # MCP / CLI エミュレーション用ループ
        for line in sys.stdin:
            if not line.strip(): continue
            response = core.dispatch(line)
            print(json.dumps(response, ensure_ascii=False), flush=True)
            # バックグラウンドでセッションのクリーンアップ（GC）
            core.manager.gc()
