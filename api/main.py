import os
import sys
import json
import argparse

# パス解決: lib を見つけられるようにする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# インポート (FastAPIとEngineを確実に読み込む)
from fastapi import FastAPI
from lib.akasha.engine import AkashaEngine

app = FastAPI()
engine = AkashaEngine()

def handle_stdio():
    # stdoutを汚さないよう stderr に出力
    print("[Internal] Akasha Engine: stdio mode activated.", file=sys.stderr)
    
    last_keys = []  # シリアル番号用キャッシュ
    it_key = None   # $it 用キャッシュ

    for line in sys.stdin:
        try:
            req = json.loads(line)
            cmd = req.get("cmd")
            args = req.get("args", [])
            
            # Key解決関数: シリアル番号(0,1,2) or $it or 生のKey
            def resolve_key(target):
                nonlocal it_key
                if not target or target == "$it":
                    return it_key
                if str(target).isdigit():
                    idx = int(target)
                    if 0 <= idx < len(last_keys):
                        return last_keys[idx]
                return target

            res = None
            
            if cmd == "write" and args:
                res = engine.commit(args[0])
                it_key = res.get("key")
            elif cmd == "list":
                limit = int(args[0]) if args else 10
                res = engine.stream(limit=limit)
                last_keys = [item['key'] for item in res]
                if last_keys: it_key = last_keys[0]
            elif cmd == "read":
                k = resolve_key(args[0] if args else None)
                atoms = engine.stream(limit=1000)
                res = next((a for a in atoms if a['key'] == k), {"status": "error", "message": "Not found"})
                if isinstance(res, dict) and "key" in res: it_key = res["key"]
            elif cmd == "affix" and len(args) >= 2:
                res = engine.affix(resolve_key(args[0]), args[1])
            elif cmd == "set_add" and len(args) >= 1:
                set_name = args[0]
                k = resolve_key(args[1] if len(args) > 1 else None)
                res = engine.add_to_set(set_name, k)
            elif cmd == "set_list":
                res = engine.list_sets()
            elif cmd == "set_members" and args:
                res = engine.get_set_members(args[0])
            elif cmd == "delete_atom":
                res = engine.delete_atom(resolve_key(args[0] if args else None))
            elif cmd == "help":
                res = {
                    "status": "ok", 
                    "commands": {
                        "write": "content", "list": "limit", "read": "ID/$it", 
                        "affix": "ID trait", "set_add": "name ID", "set_list": "-",
                        "delete_atom": "ID"
                    }
                }
            
            # 結果を標準出力へ
            print(json.dumps(res or {"status": "error", "message": "Unknown command"}, ensure_ascii=False), flush=True)
            
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true")
    args, _ = parser.parse_known_args()
    if args.stdio:
        handle_stdio()
    else:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
