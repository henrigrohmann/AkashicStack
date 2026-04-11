import sys
import os
import json
import argparse
from lib.akasha.manager import AkashaManager
from lib.akasha.resolver import ContextResolver

sys.path.append(os.getcwd())

class AkashaCore:
    def __init__(self, mode="seeds"):
        self.manager = AkashaManager(is_enterprise=(mode == "enterprise"))
        self.history_cache = {}

    def dispatch(self, json_rpc_req):
        try:
            req = json.loads(json_rpc_req) if isinstance(json_rpc_req, str) else json_rpc_req
            method = req.get("method")
            params = req.get("params", {})
            client_id = params.get("client_id", "me")
            req_id = req.get("id")

            session = self.manager.get_session(client_id)
            history = self.history_cache.get(client_id, [])

            if method == "write":
                res = session.engine.commit(params.get("text", ""))
                session.it_key = res.get("key")
                self._update_history(client_id, res.get("key"))
                return self._format_response(res, req_id)

            elif method == "read":
                resolved_id = ContextResolver.resolve(session, params, history)
                atoms = session.engine.stream(limit=1000)
                result = next((a for a in atoms if a['key'] == resolved_id), {"error": "not_found"})
                return self._format_response(result, req_id)

            elif method == "list":
                limit = params.get("limit", 10)
                res = session.engine.stream(limit=limit)
                # 一覧表示時も履歴キャッシュを更新（$0, $1...用）
                keys = [item['key'] for item in res]
                self.history_cache[client_id] = keys
                return self._format_response(res, req_id)

            elif method == "affix":
                resolved_id = ContextResolver.resolve(session, params, history)
                trait = params.get("trait")
                if not trait: return self._format_error(-32602, "Trait required")
                res = session.engine.affix(resolved_id, trait)
                return self._format_response(res, req_id)

            elif method == "set":
                sub = params.get("sub")
                name = params.get("name")
                if sub == "add":
                    resolved_id = ContextResolver.resolve(session, params, history)
                    res = session.engine.add_to_set(name, resolved_id)
                elif sub == "list":
                    res = session.engine.list_sets()
                elif sub == "members":
                    res = session.engine.get_set_members(name)
                else:
                    return self._format_error(-32602, "Invalid sub-command")
                return self._format_response(res, req_id)

            elif method == "help":
                return self._format_response({
                    "write <text>": "Atomを記録",
                    "list <n>": "最近のn件を表示",
                    "read <id|$it>": "詳細表示",
                    "affix <id> <tag>": "タグ付与",
                    "set add <name> <id>": "集合に追加",
                    "set list": "集合一覧",
                    "set members <name>": "集合の中身を表示"
                }, req_id)

            return self._format_error(-32601, f"Method '{method}' not found", req_id)
        except Exception as e:
            return self._format_error(-32603, str(e))

    def _update_history(self, client_id, key):
        if client_id not in self.history_cache: self.history_cache[client_id] = []
        if key not in self.history_cache[client_id]:
            self.history_cache[client_id].insert(0, key)
            self.history_cache[client_id] = self.history_cache[client_id][:20]

    def _format_response(self, result, req_id):
        return {"jsonrpc": "2.0", "result": result, "id": req_id}

    def _format_error(self, code, message, req_id=None):
        return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": req_id}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="seeds")
    parser.add_argument("--stdio", action="store_true")
    args = parser.parse_args()
    core = AkashaCore(mode=args.mode)
    if args.stdio:
        for line in sys.stdin:
            if not line.strip(): continue
            print(json.dumps(core.dispatch(line), ensure_ascii=False), flush=True)
