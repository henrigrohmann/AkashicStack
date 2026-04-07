# api/main.py (フルコード)

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
async def create_chunk(input: ChunkInput): 
    return engine.commit(input.content)

@app.get("/chunks/{key}", operation_id="read")
async def read_chunk(key: str):
    res = engine.fetch(key)
    if "error" in res: raise HTTPException(status_code=404, detail="Not Found")
    return res

@app.put("/chunks/{key}/traits", operation_id="tag")
async def add_trait(key: str, input: TraitInput): 
    return engine.affix(key, input.trait)

@app.get("/chunks", operation_id="list")
async def list_chunks(limit: int = 20): 
    return engine.stream(limit=limit)

# --- Set Operations: CLIとの互換性を最大化 ---

@app.post("/sets", operation_id="set_create")
async def create_set(input: SetInput): 
    return engine.create_set(input.name)

@app.post("/sets/{name}/items", operation_id="set_add")
async def add_to_set(name: str, key: Optional[str] = None): 
    # keyが渡されない場合はエラーを返さず、エンジン側で$itの不備をチェックする
    if not key:
        return {"key": None, "error": "key_required_from_cli"}
    return engine.add_to_set(name, key)

@app.get("/sets/{name}", operation_id="set_list")
async def list_set_items(name: str): 
    return engine.fetch_set(name)
