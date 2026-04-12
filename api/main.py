import sys, os, json, argparse, uvicorn
from fastapi import FastAPI, Request
from lib.akasha.manager import AkashaManager
from lib.akasha.resolver import ContextResolver

sys.path.append(os.getcwd())

class AkashaCore:
    def __init__(self):
        self.manager = AkashaManager()
        self.node_id = os.getenv("AKASHA_NODE_ID", "Akasha-Main-Core")
        self.history_cache = {} # $it解決用の短期メモリ

    def dispatch(self, json_rpc_req):
        try:
            req = json.loads(json_rpc_req) if isinstance(json_rpc_req, str) else json_rpc_req
            method, params, req_id = req.get("method"), req.get("params", {}), req.get("id")
            client_id = params.get("client_id", "guest")
            secret = params.get("secret", "")

            if method == "signup":
                success = self.manager.register(params.get("new_id"), params.get("new_secret"))
                return self._format_response({"success": success}, req_id)

            role = self.manager.authenticate(client_id, secret) or "leaf"
            session = self.manager.get_session(client_id, role)
            history = self.history_cache.get(client_id, [])

            # --- Nucleus Access (Admin Only & Dedicated Method) ---
            if method.startswith("vault_"):
                if role != "admin": return self._format_error(-32000, "Permission Denied", req_id)
                if method == "vault_set":
                    session.nucleus.vault_store(params["cat"], params["id"], params["data"])
                    return self._format_response("Stored in Nucleus", req_id)
                if method == "vault_get":
                    res = session.nucleus.vault_retrieve(params["cat"], params["id"])
                    return self._format_response(res, req_id)

            # --- Cortex/Hippocampus Operations ---
            if method == "write":
                res = session.local_cortex.commit(params.get("text", ""))
                key = res.get("key")
                session.it_key = key
                self._update_history(client_id, key)
                return self._format_response(res, req_id)

            elif method == "read":
                rid = ContextResolver.resolve(session, params, history)
                # Local -> Global の順で実体を取得
                for cortex in [session.local_cortex, session.global_cortex]:
                    res = cortex.stream(100)
                    atom = next((a for a in res if a['key'] == rid), None)
                    if atom: return self._format_response(atom, req_id)
                return self._format_response({"error": "not_found", "resolved_id": rid}, req_id)

            elif method == "list":
                return self._format_response(session.local_cortex.stream(params.get("limit", 10)), req_id)

            elif method == "initialize":
                return self._format_response({
                    "serverInfo": {"name": self.node_id, "role": role},
                    "protocolVersion": "2024-11-05"
                }, req_id)

            return self._format_error(-32601, f"Method {method} not found", req_id)
        except Exception as e: return self._format_error(-32603, str(e))

    def _update_history(self, cid, key):
        if cid not in self.history_cache: self.history_cache[cid] = []
        if key not in self.history_cache[cid]:
            self.history_cache[cid].insert(0, key)
            self.history_cache[cid] = self.history_cache[cid][:20]

    def _format_response(self, result, rid): return {"jsonrpc": "2.0", "result": result, "id": rid}
    def _format_error(self, code, msg, rid=None): return {"jsonrpc": "2.0", "error": {"code": code, "message": msg}, "id": rid}

app = FastAPI()
core = AkashaCore()

@app.post("/rpc")
async def rpc_endpoint(request: Request):
    return core.dispatch(await request.json())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.stdio:
        for line in sys.stdin:
            if line.strip(): print(json.dumps(core.dispatch(line), ensure_ascii=False), flush=True)
    else:
        uvicorn.run(app, host="0.0.0.0", port=args.port)
