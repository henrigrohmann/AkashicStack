import sys, os, json, argparse, uvicorn
from fastapi import FastAPI, Request
from lib.akasha.manager import AkashaManager
from lib.akasha.resolver import ContextResolver

sys.path.append(os.getcwd())

class AkashaCore:
    def __init__(self):
        self.manager = AkashaManager()
        self.node_id = os.getenv("AKASHA_NODE_ID", "Akasha-Main-Core")

    def dispatch(self, json_rpc_req):
        try:
            req = json.loads(json_rpc_req) if isinstance(json_rpc_req, str) else json_rpc_req
            method, params, req_id = req.get("method"), req.get("params", {}), req.get("id")
            client_id = params.get("client_id", "guest")
            secret = params.get("secret", "")

            # --- Authentication / Registration ---
            if method == "signup":
                success = self.manager.register(params.get("new_id"), params.get("new_secret"))
                return self._format_response({"success": success}, req_id)

            # セッション取得 (認証済みの場合はRoleを適用)
            role = self.manager.authenticate(client_id, secret) or "leaf"
            session = self.manager.get_session(client_id, role)

            # --- Nucleus Access (Admin Only) ---
            if method.startswith("vault_"):
                if role != "admin": return self._format_error(-32000, "Permission Denied", req_id)
                if method == "vault_set":
                    session.nucleus.vault_store(params["cat"], params["id"], params["data"])
                    return self._format_response("Stored", req_id)
                if method == "vault_get":
                    res = session.nucleus.vault_retrieve(params["cat"], params["id"])
                    return self._format_response(res, req_id)

            # --- Cortex/Hippocampus Operations ---
            if method == "write":
                # 書き込み先は常に Local Cortex
                res = session.local_cortex.commit(params.get("text", ""))
                session.it_key = res.get("key")
                return self._format_response(res, req_id)

            elif method == "read":
                rid = ContextResolver.resolve(session, params, [])
                # Local -> Global の順で検索
                res = session.local_cortex.stream(100) # 簡易検索
                atom = next((a for a in res if a['key'] == rid), None)
                if not atom:
                    res = session.global_cortex.stream(100)
                    atom = next((a for a in res if a['key'] == rid), None)
                return self._format_response(atom or {"error": "not_found"}, req_id)

            elif method == "list":
                # 自分のローカルヒストリを表示
                return self._format_response(session.local_cortex.stream(params.get("limit", 10)), req_id)

            elif method == "initialize":
                return self._format_response({
                    "serverInfo": {"name": self.node_id, "role": role},
                    "protocolVersion": "2024-11-05"
                }, req_id)

            elif method == "help":
                return self._format_response({
                    "signup": "Register new Cell",
                    "write/read/list": "Memory operations",
                    "vault_set/get": "Nucleus management (Admin only)"
                }, req_id)

            return self._format_error(-32601, f"Method {method} not found", req_id)
        except Exception as e: return self._format_error(-32603, str(e))

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
