from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lib.akasha.engine import AkashaEngine

app = FastAPI(title="Akashic Stack API")
engine = AkashaEngine()

class ChunkInput(BaseModel):
    content: str

class TraitInput(BaseModel):
    trait: str

@app.post("/chunks", operation_id="write", summary="Atomの刻印")
async def create_chunk(input: ChunkInput):
    """新しい文章を永続化し、ハッシュキーを生成して返します。"""
    return engine.commit(input.content)

@app.get("/chunks/{key}", operation_id="read", summary="Atomの参照")
async def read_chunk(key: str):
    """指定されたキー（ハッシュ）に紐づくデータと特性を取得します。"""
    result = engine.fetch(key)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return result

@app.put("/chunks/{key}/traits", operation_id="tag", summary="特性(Trait)の付与")
async def add_trait(key: str, input: TraitInput):
    """指定されたAtomに対して、新しい特性（タグ）を付与します。"""
    result = engine.affix(key, input.trait)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return result

@app.get("/chunks", operation_id="list", summary="Atomの一覧取得")
async def list_chunks(limit: int = 20):
    """最近保存されたAtomを書き込み順に取得します。"""
    return engine.stream(limit=limit)
