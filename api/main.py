import os
import sys
import json
import argparse

# パス解決: 親ディレクトリの lib をインポート可能にする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from fastapi import FastAPI
    from lib.akasha.engine import AkashaEngine
except ImportError as e:
    print(f"[Error] Dependency missing: {e}", file=sys.stderr)
    sys.exit(1)

app = FastAPI()
engine = AkashaEngine()

def handle_stdio():
    # CLI側の Adapter が読み取るまで、このメッセージがプロンプトのトリガーになる
    print("[Internal] Akasha Engine: stdio mode activated.", file=sys.stderr)
    
    last_keys = []  # シリアル番号(0, 1, 2...)用キャッシュ
    it_key = None   # $it 用キャッシュ

    for line in sys.stdin:
        try:
            line = line.strip()
            if not line:
                continue
                
            req = json.loads(line)
            cmd = req.get("cmd")
            args = req.get("args", [])
            
            # --- Key解決ロジック ---
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
            
            # --- コマンド分岐 ---
            if cmd == "write" and args:
                # スペースで区切られた引数をすべて結合して一つの content にする
                content = " ".join(args)
                res = engine.commit(content)
                if isinstance(res, dict) and res.get("key"):
                    it_key = res["key"]

            elif cmd == "list":
                limit = int(args[0]) if (args and args[0].isdigit()) else 10
                res = engine.stream(limit=limit)
                # シリアル番号用にキャッシュを更新
                last_keys = [item['key'] for item in res]
                if last_keys:
                    it_key = last_keys[0]

            elif cmd == "read":
                k = resolve_key(args[0] if args else None)
                atoms = engine.stream(limit=1000)
                res = next((a for a in atoms if a['key'] == k), {"status": "error", "message": "Not found"})
                if isinstance(res, dict) and "key" in res:
                    it_key = res["key"]

            elif cmd == "affix" and len(args) >= 2:
                target_key = resolve_key(args[0])
                trait = args[1]
                res = engine.affix(target_key, trait)

            elif cmd == "set_add" and len(args) >= 1:
                set_name = args[0]
                target_key = resolve_key(args[1] if len(args) > 1 else None)
                res = engine.add_to_set(set_name, target_key)

            elif cmd == "set_list":
                res = engine.list_sets()

            elif cmd == "set_members" and args:
                res = engine.get_set_members(args[0])

            elif cmd == "remove_trait" and len(args) >= 2:
                res = engine.remove_trait(resolve_key(args[0]), args[1])

            elif cmd == "delete_atom" and args:
                res = engine.delete_atom(resolve_key(args[0]))

            elif cmd == "help":
                res = {
                    "status": "ok", 
                    "commands": {
                        "write": "<content>", 
                        "list": "[limit]", 
                        "read": "<ID|$it>", 
                        "affix": "<ID|$it> <trait>", 
                        "set_add": "<name> <ID|$it>", 
                        "set_list": "-",
                        "delete_atom": "<ID|$it>"
                    }
                }
            
            # 結果を JSON で一行出力 (flush必須)
            print(json.dumps(res or {"status": "error", "message": "Unknown command"}, ensure_ascii=False), flush=True)
            
        except Exception as e:
            error_res = {"status": "error", "message": str(e)}
            print(json.dumps(error_res, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true")
    args, _ = parser.parse_known_args()

    if args.stdio:
        handle_stdio()
    else:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
