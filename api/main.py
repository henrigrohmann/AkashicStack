from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from lib.akasha.engine import AkashaEngine

app = FastAPI(title="Akashic Stack API")
engine = AkashaEngine()

# --- Data Models ---

class ChunkInput(BaseModel):
    content: str

class TraitInput(BaseModel):
    trait: str

class SetInput(BaseModel):
    name: str

# --- Endpoints ---

@app.post("/chunks", operation_id="write", summary="Atomの刻印")
async def create_chunk(input: ChunkInput):
    """新しい文章を永続化し、ハッシュキー(key)を返します。"""
    return engine.commit(input.content)

@app.get("/chunks/{key}", operation_id="read", summary="Atomの参照")
async def read_chunk(key: str):
    """指定されたキーに紐づくデータと特性を取得します。"""
    result = engine.fetch(key)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return result

@app.put("/chunks/{key}/traits", operation_id="tag", summary="特性(Trait)の付与")
async def add_trait(key: str, input: TraitInput):
    """指定されたAtomにタグを付与します。"""
    result = engine.affix(key, input.trait)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/chunks", operation_id="list", summary="最近のAtom一覧")
async def list_chunks(limit: int = 20):
    """最近のAtomを時系列順に取得します。"""
    return engine.stream(limit=limit)

# --- Set Operations ---

@app.post("/sets", operation_id="set_create", summary="集合の新規作成")
async def create_set(input: SetInput):
    """新しい集合ノードを作成します。"""
    # inputそのものではなく、input.name(str)を渡す
    return engine.create_set(input.name)

@app.post("/sets/{name}/items", operation_id="set_add", summary="集合への追加")
async def add_to_set(name: str, key: Optional[str] = None):
    """指定した集合にAtomを追加します。"""
    return engine.add_to_set(name, key)

@app.get("/sets/{name}", operation_id="set_list", summary="集合内のAtom取得")
async def list_set_items(name: str, limit: int = 20):
    """集合に含まれるAtomを取得します。"""
    return engine.fetch_set(name, limit=limit)
