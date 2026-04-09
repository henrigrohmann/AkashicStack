import os
import sys
import json
import argparse

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
from lib.akasha.engine import AkashaEngine

app = FastAPI()
engine = AkashaEngine()

def handle_stdio():
    print("[Internal] Akasha Engine: stdio mode activated.", file=sys.stderr)
    
    last_keys = []  # シリアル番号用キャッシュ
    it_key = None   # $it 用キャッシュ

    for line in sys.stdin:
        try:
            req = json.loads(line)
            cmd = req.get("cmd")
            args = req.get("args", [])
            
            def resolve_key(target):
                nonlocal it_key
                if not target or target == "$it": return it_key
                if str(target).isdigit():
                    idx = int(target)
                    return last_keys[idx] if 0 <= idx < len(last_keys) else target
                return target

            res = None
            if cmd == "write":
                res = engine.commit(args[0])
                it_key = res.get("key")
            elif cmd == "list":
                res = engine.stream(limit=int(args[0]) if args else 10)
                last_keys = [item['key'] for item in res]
                if last_keys: it_key = last_keys[0]
            elif cmd == "read":
                k = resolve_key(args[0] if args else None)
                atoms = engine.stream(limit=1000)
                res = next((a for a in atoms if a['key'] == k), {"error": "Not found"})
                if "key" in res: it_key = res["key"]
            elif cmd == "affix":
                res = engine.affix(resolve_key(args[0]), args[1])
            elif cmd == "set_add":
                res = engine.add_to_set(args[0], resolve_key(args[1] if len(args)>1 else None))
            elif cmd == "delete_atom":
                res = engine.delete_atom(resolve_key(args[0] if args else None))
            elif cmd == "help":
                res = {"status": "ok", "commands": {"write": "content", "list": "limit", "read": "id/$it", "affix": "id trait", "set_add": "name id"}}
            
            print(json.dumps(res or {"error": "command fail"}, ensure_ascii=False), flush=True)
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}), flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true")
    args, _ = parser.parse_known_args()
    if args.stdio: handle_stdio()
    else:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
