from fastapi import FastAPI, Body
from pydantic import BaseModel
from lib.akasha.engine import AkashaEngine

app = FastAPI()
engine = AkashaEngine()

# リクエストボディの定義を新体系に合わせる
class ChunkCreate(BaseModel):
    content: str

@app.post("/chunks")
async def create_chunk(chunk: ChunkCreate):
    # uidなどを要求せず、contentだけでcommitを呼ぶ
    result = engine.commit(chunk.content)
    return result
