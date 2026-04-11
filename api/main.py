import sys, os, json, argparse, uvicorn
from fastapi import FastAPI, Request
from lib.akasha.manager import AkashaManager
from lib.akasha.resolver import ContextResolver

sys.path.append(os.getcwd())

class AkashaCore:
    def __init__(self, mode="seeds"):
        self.manager = AkashaManager(is_enterprise=(mode == "enterprise"))
        self.history_cache = {}
        # 個体識別ID（環境変数から取得、なければデフォルト）
        self.node_id = os.getenv("AKASHA_NODE_ID", "Akasha-Sprout-Alpha")

    def dispatch(self, json_rpc_req):
        try:
            req = json.loads(json_rpc_req) if isinstance(json_rpc_req, str) else json_rpc_req
            method = req.get("method")
            params = req.get("params", {})
            client_id = params.get("client_id", "me")
            req_id = req.get("id")

            session = self.manager.get_session(client_id)
            history = self.history_cache.get(client_id, [])

            # --- MCP Lifecycle: Initialize ---
            if method == "initialize":
                return self._format_response({
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {"subscribe": False}
                    },
                    "serverInfo": {
                        "name": self.node_id,
                        "version": "0.4.0",
                        "description": "Akasha Context Engine Node"
                    }
                }, req_id)

            # --- MCP Tools: List & Call ---
            elif method == "tools/list":
                return self._format_response({
                    "tools": [
                        {"name": "write", "description": "新しいAtomを記録する", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}},
                        {"name": "affix", "description": "Atomにタグ(Trait)を付与する", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "trait": {"type": "string"}}}},
                        {"name": "set_add", "description": "Atomを集合に追加する", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "id": {"type": "string"}}}}
                    ]
                }, req_id)

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                if tool_name == "write":
                    res = session.engine.commit(tool_args.get("text", ""))
                    self._update_history(client_id, res.get("key"))
                    return self._format_response({"content": [{"type": "text", "text": json.dumps(res)}]}, req_id)
                
                elif tool_name == "affix":
                    rid = ContextResolver.resolve(session, tool_args, history)
                    res = session.engine.affix(rid, tool_args.get("trait"))
                    return self._format_response({"content": [{"type": "text", "text": json.dumps(res)}]}, req_id)

            # --- MCP Resources: List & Read ---
            elif method == "resources/list":
                res = session.engine.stream(limit=20)
                resources = [{
                    "uri": f"akasha://{client_id}/atoms/{item['key']}",
                    "name": item['content'][:20] + "...",
                    "mimeType": "application/json"
                } for item in res]
                return self._format_response({"resources": resources}, req_id)

            # --- 既存の互換メソッド (CLI用) ---
            elif method in ["write", "list", "read", "affix", "set", "help"]:
                return self._legacy_dispatch(method, params, session, history, client_id, req_id)

            return self._format_error(-32601, f"Method '{method}' not found", req_id)
        except Exception as e:
            return self._format_error(-32603, str(e))

    def _legacy_dispatch(self, method, params, session, history, client_id, req_id):
        # 以前実装したロジックをここに集約
        if method == "write":
            res = session.engine.commit(params.get("text", ""))
            self._update_history(client_id, res.get("key"))
            return self._format_response(res, req_id)
        elif method == "list":
            res = session.engine.stream(limit=params.get("limit", 10))
            self.history_cache[client_id] = [i['key'] for i in res]
            return self._format_response(res, req_id)
        elif method == "read":
            rid = ContextResolver.resolve(session, params, history)
            atoms = session.engine.stream(limit=1000)
            res = next((a for a in atoms if a['key'] == rid), {"error": "not_found"})
            return self._format_response(res, req_id)
        # (以下略: affix, set, help も同様に格納)
        return self._format_error(-32601, "Legacy method error", req_id)

    def _update_history(self, cid, key):
        if cid not in self.history_cache: self.history_cache[cid] = []
        if key not in self.history_cache[cid]:
            self.history_cache[cid].insert(0, key)
            self.history_cache[cid] = self.history_cache[cid][:20]

    def _format_response(self, result, rid):
        return {"jsonrpc": "2.0", "result": result, "id": rid}

    def _format_error(self, code, msg, rid=None):
        return {"jsonrpc": "2.0", "error": {"code": code, "message": msg}, "id": rid}

app = FastAPI(title="Akasha MCP Server")
core = AkashaCore()

@app.post("/rpc")
@app.post("/mcp")
async def rpc_endpoint(request: Request):
    body = await request.json()
    return core.dispatch(body)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.stdio:
        for line in sys.stdin:
            if not line.strip(): continue
            print(json.dumps(core.dispatch(line), ensure_ascii=False), flush=True)
    else:
        uvicorn.run(app, host="0.0.0.0", port=args.port)
