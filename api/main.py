from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from lib.akasha.engine import AkashaEngine

app = FastAPI(title="Akashic Stack API")

# エンジンの初期化（環境変数などでDBパスを切り替え可能にする準備）
# 明示的にインスタンス化することで、起動時の_bootstrapを確実に行う
engine = AkashaEngine()

class ChunkInput(BaseModel): content: str
class TraitInput(BaseModel): trait: str
class SetInput(BaseModel): name: str

@app.post("/chunks", operation_id="write")
async def create_chunk(input: ChunkInput): 
    # engine.commit 内で _write_with_journal が呼ばれ、アトミックに保存されます
    return engine.commit(input.content)

@app.get("/chunks/{key}", operation_id="read")
async def read_chunk(key: str):
    res = engine.fetch(key)
    if "error" in res: 
        raise HTTPException(status_code=404, detail="Not Found")
    return res

@app.put("/chunks/{key}/traits", operation_id="tag")
async def add_trait(key: str, input: TraitInput): 
    res = engine.affix(key, input.trait)
    if "error" in res:
        raise HTTPException(status_code=404, detail="Key Not Found")
    return res

@app.get("/chunks", operation_id="list")
async def list_chunks(limit: int = 20): 
    return engine.stream(limit=limit)

# --- Set Operations: CLIとの互換性を最大化 ---

@app.post("/sets", operation_id="set_create")
async def create_set(input: SetInput): 
    return engine.create_set(input.name)

@app.post("/sets/{name}/items", operation_id="set_add")
async def add_to_set(name: str, key: Optional[str] = None): 
    # CLI ($it) からの入力が空の場合のガード
    if not key or key == "None":
        # 422を避けてカスタムエラーを返すことで、CLI側のデバッグを容易にする
        return {"key": key, "error": "key_invalid_or_empty_from_cli"}
        
    res = engine.add_to_set(name, key)
    if "error" in res:
        raise HTTPException(status_code=404, detail=f"Key {key} not found for set {name}")
    return res

@app.get("/sets/{name}", operation_id="set_list")
async def list_set_items(name: str): 
    return engine.fetch_set(name)
