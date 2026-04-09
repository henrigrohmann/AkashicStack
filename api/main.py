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
    
    # セッション内での一時キャッシュ
    last_keys = []  # シリアル番号用
    it_key = None   # $it 用

    for line in sys.stdin:
        try:
            req = json.loads(line)
            cmd = req.get("cmd")
            args = req.get("args", [])
            
            # --- Keyの解決ロジック ---
            def resolve_key(target):
                nonlocal it_key
                if not target or target == "$it":
                    return it_key
                if target.isdigit(): # シリアル番号
                    idx = int(target)
                    if 0 <= idx < len(last_keys):
                        return last_keys[idx]
                return target

            res = None
            
            if cmd == "write" and args:
                res = engine.commit(args[0])
                if res.get("key"): it_key = res["key"]

            elif cmd == "list":
                limit = int(args[0]) if args else 10
                res = engine.stream(limit=limit)
                # シリアル番号用にKeyをキャッシュ
                last_keys = [item['key'] for item in res]
                if last_keys: it_key = last_keys[0]

            elif cmd == "read":
                key = resolve_key(args[0] if args else None)
                atoms = engine.stream(limit=1000)
                res = next((a for a in atoms if a['key'] == key), {"status": "error", "message": "Not found"})
                if res.get("key"): it_key = res["key"]

            elif cmd == "affix" and args:
                key = resolve_key(args[0])
                trait = args[1] if len(args) > 1 else None
                res = engine.affix(key, trait)

            elif cmd == "set_add" and args:
                set_name = args[0]
                key = resolve_key(args[1] if len(args) > 1 else None)
                res = engine.add_to_set(set_name, key)

            elif cmd == "delete_atom":
                key = resolve_key(args[0] if args else None)
                res = engine.delete_atom(key)
            
            # (他のコマンドも同様に resolve_key を通す)
            elif cmd == "help":
                res = {"status": "ok", "message": "Manual: write, list, read, affix, set_add, delete_atom"}
            else:
                res = res or {"status": "error", "message": "Unknown command"}
            
            print(json.dumps(res, ensure_ascii=False), flush=True)
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}), flush=True)

if __name__ == "__main__":
    # 既存の argparse / uvicorn 起動ロジック
