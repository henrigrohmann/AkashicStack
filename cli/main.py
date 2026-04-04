import typer
import httpx

cli = typer.Typer()
API_URL = "http://localhost:8000"

@cli.command()
def watch():
    """バックエンドに溜まっていくチャンクをリアルタイム監視(簡易版)"""
    typer.echo("Monitoring Akasha memory status...")
    # ここにWebSocketまたはポーリングによる監視ロジックを実装

@cli.command()
def seed():
    """テスト用の初期データを投入"""
    test_data = [
        {"uid": "U01", "body": "今日は #Harmonia の設計。", "meta": {"tags": ["Harmonia"]}},
        {"uid": "U02", "body": "#Akasha は静的な記憶。", "meta": {"tags": ["Akasha"]}}
    ]
    for d in test_data:
        httpx.post(f"{API_URL}/chunks", json=d)
    typer.echo("Seeding completed.")

if __name__ == "__main__":
    cli()

