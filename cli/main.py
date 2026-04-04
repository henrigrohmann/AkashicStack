import typer
import httpx
import json

app = typer.Typer()
API_URL = "http://localhost:8000"

@app.command()
def write(content: str):
    """新しいチャンクを書き込む"""
    # CLI側でエスケープ処理などは暗黙的に行われる（引数として受け取るため）
    resp = httpx.post(f"{API_URL}/chunks", json={"content": content})
    typer.echo(json.dumps(resp.json(), indent=2))

@app.command()
def read(key: str):
    """特定のキーの情報をJSONで表示する"""
    resp = httpx.get(f"{API_URL}/chunks/{key}")
    typer.echo(json.dumps(resp.json(), indent=2))

@app.command()
def tag(key: str, trait: str):
    """チャンクにタグ（Trait）を付与する"""
    resp = httpx.put(f"{API_URL}/chunks/{key}/traits", json={"trait": trait})
    typer.echo(json.dumps(resp.json(), indent=2))

@app.command()
def find(traits: list[str]):
    """特定のタグを持つチャンクを検索する"""
    # query parameterとして送信
    params = {"q": ",".join(traits)}
    resp = httpx.get(f"{API_URL}/traits/search", params=params)
    typer.echo(json.dumps(resp.json(), indent=2))

@app.command()
def list(limit: int = 20):
    """直近のチャンクを一覧表示する"""
    resp = httpx.get(f"{API_URL}/chunks", params={"limit": limit})
    typer.echo(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    app()
