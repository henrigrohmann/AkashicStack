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

# --- Endpoints ---

@app.post("/chunks", operation_id="write", summary="Atomの刻印")
async def create_chunk(input: ChunkInput):
    """新しい文章を永続化し、ハッシュキー(key)を返します。"""
    return engine.commit(input.content)

@app.get("/chunks/{key}", operation_id="read", summary="Atomの参照")
async def read_chunk(key: str):
    """指定されたキーに紐づくデータと特性（Traits）を取得します。"""
    result = engine.fetch(key)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return result

@app.put("/chunks/{key}/traits", operation_id="tag", summary="特性(Trait)の付与")
async def add_trait(key: str, input: TraitInput):
    """指定されたキーのAtomに対して、新しいタグを付与します。"""
    result = engine.affix(key, input.trait)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return result

@app.get("/chunks", operation_id="list", summary="最近のAtom一覧")
async def list_chunks(limit: int = 20):
    """最近保存されたAtomを時系列順に取得します。"""
    return engine.stream(limit=limit)

@app.get("/traits/search", operation_id="find", summary="特性による検索")
async def search_by_traits(q: str):
    """タグ（カンマ区切り）を指定して、合致するAtomを検索します。"""
    traits = [t.strip() for t in q.split(",")]
    return engine.collect(traits)
