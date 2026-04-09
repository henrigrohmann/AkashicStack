import sys
import json
import argparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from lib.akasha.engine import AkashaEngine

app = FastAPI()
engine = AkashaEngine()

# --- API Data Models ---
class CommitRequest(BaseModel):
    content: str

class AffixRequest(BaseModel):
    trait: str

# --- FastAPI Routes (Existing Logic) ---
@app.post("/write")
async def write_atom(req: CommitRequest):
    return engine.commit(req.content)

@app.post("/affix/{key}")
async def affix_trait(key: str, req: AffixRequest):
    return engine.affix(key, req.trait)

# --- stdio Handler (New Logic for Dependency Inversion) ---
def handle_stdio():
    """標準入出力経由でリクエストを処理するループ"""
    print("[Internal] Akasha Engine: stdio mode activated.", file=sys.stderr)
    
    for line in sys.stdin:
        try:
            req = json.loads(line)
            cmd = req.get("cmd")
            args = req.get("args", [])
            
            # CLIからのコマンドを内部エンジンへルーティング
            if cmd == "write":
                res = engine.commit(args[0])
            elif cmd == "affix":
                res = engine.affix(args[0], args[1])
            elif cmd == "query":
                res = engine.find_by_trait(args[0])
            elif cmd == "list":
                res = engine.stream(limit=int(args[0]) if args else 10)
            else:
                res = {"status": "error", "message": f"Unknown command: {cmd}"}
            
            print(json.dumps(res, ensure_ascii=False), flush=True)
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}), flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true")
    args, unknown = parser.parse_known_args()

    if args.stdio:
        handle_stdio()
    else:
        import uvicorn
        # ポート8000で通常起動
        uvicorn.run(app, host="0.0.0.0", port=8000)
