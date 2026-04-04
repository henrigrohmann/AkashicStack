from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Akashic Stack API")
memory = AkashaEngine()

class ChunkInput(BaseModel):
    uid: str
    body: str
    meta: dict

@app.post("/chunks")
async def add_chunk(data: ChunkInput):
    c_hash = memory.put(data.body, data.meta, data.uid)
    return {"status": "stored", "hash": c_hash}

@app.get("/tags/{tag_name}")
async def get_by_tag(tag_name: str):
    # メタデータ内のタグを検索するロジック（後述のsearch拡張にて）
    return {"tag": tag_name, "chunks": []}

