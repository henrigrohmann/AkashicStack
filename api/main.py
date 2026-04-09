import os
import sys
import json
import argparse

# パス解決
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from fastapi import FastAPI
from lib.akasha.engine import AkashaEngine

app = FastAPI()
engine = AkashaEngine()

def handle_stdio():
    print("[Internal] Akasha Engine: stdio mode activated.", file=sys.stderr)
    
    COMMAND_HELP = {
        "write": "write <content> - Atomを書き込む",
        "read": "read <key> - 指定したKeyのAtomを1件取得",
        "list": "list [limit] - 最近のAtomを一覧表示",
        "affix": "affix <key> <trait> - Atomに属性(Trait)を付与",
        "query": "query <trait> - 属性でAtomを検索",
        "set_add": "set_add <set_name> <key> - 集合にAtomを追加",
        "set_list": "set_list - 存在する集合名の一覧を表示",
        "set_members": "set_members <set_name> - 集合に属するAtom一覧を表示",
        "remove_trait": "remove_trait <key> <trait> - 属性を削除",
        "delete_atom": "delete_atom <key> - Atomを完全に削除",
        "help": "help - コマンドヘルプを表示"
    }

    for line in sys.stdin:
        try:
            req = json.loads(line)
            cmd = req.get("cmd")
            args = req.get("args", [])
            
            # --- 基本操作 ---
            if cmd == "write" and args:
                res = engine.commit(args[0])
            elif cmd == "read" and args:
                atoms = engine.stream(limit=1000)
                res = next((a for a in atoms if a['key'] == args[0]), {"error": "Not found"})
            elif cmd == "list":
                res = engine.stream(limit=int(args[0]) if args else 10)
            
            # --- Trait (属性) 操作 ---
            elif cmd == "affix" and len(args) >= 2:
                res = engine.affix(args[0], args[1])
            elif cmd == "query" and args:
                res = engine.find_by_trait(args[0])
            elif cmd == "remove_trait" and len(args) >= 2:
                res = engine.remove_trait(args[0], args[1]) # Engine側に実装が必要
            
            # --- Set (集合) 操作 ---
            elif cmd == "set_add" and len(args) >= 2:
                res = engine.add_to_set(args[0], args[1])
            elif cmd == "set_list":
                res = engine.list_sets() # Engine側に実装が必要
            elif cmd == "set_members" and args:
                res = engine.get_set_members(args[0]) # Engine側に実装が必要
            
            # --- 削除系 ---
            elif cmd == "delete_atom" and args:
                res = engine.delete_atom(args[0]) # Engine側に実装が必要
            
            elif cmd == "help":
                res = {"status": "ok", "commands": COMMAND_HELP}
            else:
                res = {"status": "error", "message": f"Unknown or invalid command: {cmd}"}
            
            print(json.dumps(res, ensure_ascii=False), flush=True)
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}), flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true")
    args, unknown = parser.parse_known_args()
    if args.stdio: handle_stdio()
    else:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
