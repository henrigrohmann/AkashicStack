from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from lib.akasha.engine import AkashaEngine

app = FastAPI()
# エンジンを初期化（ここでディレクトリ作成とDB初期化が走ります）
engine = AkashaEngine()

# --- Data Models (Request/Response) ---

class ChunkInput(BaseModel):
    content: str

class TraitInput(BaseModel):
    trait: str

# --- Endpoints ---

@app.post("/chunks")
async def create_chunk(input: ChunkInput):
    """新しい文章を永続化し、ハッシュキーを返す"""
    return engine.commit(input.content)

@app.get("/chunks/{key}")
async def read_chunk(key: str):
    """キーに紐づくデータとタグを取得する"""
    result = engine.fetch(key)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return result

@app.get("/chunks")
async def list_chunks(limit: int = 20):
    """直近のデータを一覧表示する"""
    return engine.stream(limit=limit)

@app.put("/chunks/{key}/traits")
async def add_trait(key: str, input: TraitInput):
    """タグ（Trait）を付与する"""
    result = engine.affix(key, input.trait)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return result

@app.get("/traits/search")
async def search_by_traits(q: str):
    """タグ（カンマ区切り）でデータを検索する"""
    traits = [t.strip() for t in q.split(",")]
    return engine.collect(traits)
