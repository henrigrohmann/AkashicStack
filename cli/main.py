import shlex
from lib.akasha.client import AkashaClient
from rich.console import Console
from rich.panel import Panel

console = Console()

def main():
    # 通信レイヤーのインスタンス化
    client = AkashaClient(mode="stdio")
    
    # MCP初期化のシミュレーション（人間がやる対話）
    init_res = client.initialize()
    node_name = init_res.get("result", {}).get("serverInfo", {}).get("name", "Unknown")
    
    console.print(Panel(f"[bold green]Connected to: {node_name}[/bold green]\nMCP Version: {init_res.get('result', {}).get('protocolVersion')}"))

    while True:
        try:
            line = input(f"{node_name}> ").strip()
            if not line or line.lower() in ["exit", "quit"]: break
            
            parts = shlex.split(line)
            cmd = parts[0]
            
            # MCP/JSON-RPC へのマッピング
            if cmd == "write":
                res = client.write(parts[1])
            elif cmd == "list":
                res = client.list_atoms(int(parts[1]) if len(parts) > 1 else 10)
            else:
                res = client.send(cmd, {"args": parts[1:]}) # 未定義コマンドもそのまま投げてみる
            
            console.print(res)
                
        except Exception as e:
            console.print(f"[red]CLI Error: {e}[/red]")

if __name__ == "__main__":
    main()
