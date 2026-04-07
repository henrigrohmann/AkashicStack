from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from lib.akasha.engine import AkashaEngine

app = FastAPI(title="Akashic Stack API")
engine = AkashaEngine()

class ChunkInput(BaseModel): content: str
class TraitInput(BaseModel): trait: str
class SetInput(BaseModel): name: str

@app.post("/chunks", operation_id="write")
async def create_chunk(input: ChunkInput): return engine.commit(input.content)

@app.get("/chunks/{key}", operation_id="read")
async def read_chunk(key: str):
    res = engine.fetch(key)
    if "error" in res: raise HTTPException(status_code=404, detail="Not Found")
    return res

@app.put("/chunks/{key}/traits", operation_id="tag")
async def add_trait(key: str, input: TraitInput):
    return engine.affix(key, input.trait)

# --- 集合系: ここが修正ポイント ---

@app.post("/sets", operation_id="set_create")
async def create_set(input: SetInput):
    return engine.create_set(input.name)

@app.post("/sets/{name}/items", operation_id="set_add")
async def add_to_set(name: str, key: Optional[str] = None):
    # クエリパラメータ ?key=... が空ならCLIの不備を通知
    if not key:
        return {"key": None, "error": "key_required"}
    return engine.add_to_set(name, key)

@app.get("/sets/{name}", operation_id="set_list")
async def list_set_items(name: str):
    return engine.fetch_set(name)
