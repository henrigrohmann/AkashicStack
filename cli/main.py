import shlex
import argparse
from lib.akasha.client import AkashaClient
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", help="HTTP endpoint (e.g. http://localhost:8000)")
    args = parser.parse_args()

    # モードの選択
    if args.http:
        client = AkashaClient(mode="http", endpoint=args.http)
        console.print(f"[bold yellow]Mode: HTTP Network ({args.http})[/bold yellow]")
    else:
        client = AkashaClient(mode="stdio")
        console.print("[bold cyan]Mode: stdio (Subprocess)[/bold cyan]")

    # 1. MCP Initialize (挨拶)
    console.print("\n[dim]Sending 'initialize' to server...[/dim]")
    init_res = client.call("initialize")
    
    server_info = init_res.get("result", {}).get("serverInfo", {})
    node_id = server_info.get("name", "Unknown")
    
    console.print(Panel(
        f"Connected to Akasha Node: [bold green]{node_id}[/bold green]\n"
        f"Version: {server_info.get('version')}\n"
        f"Protocol: {init_res.get('result', {}).get('protocolVersion')}",
        title="MCP Session Established"
    ))

    # 2. 対話ループ
    while True:
        try:
            line = input(f"{node_id} > ").strip()
            if not line or line.lower() in ["exit", "quit"]: break
            
            parts = shlex.split(line)
            cmd = parts[0]
            
            # MCP Tool Call シミュレーション
            # ここでは便宜上、従来のメソッド名で入力しても MCP 形式へ変換する
            res = client.call(cmd, {"text": parts[1]} if cmd == "write" and len(parts)>1 else {})
            
            # 結果をJSONとして美しく表示
            json_str = json.dumps(res, indent=2, ensure_ascii=False)
            console.print(Syntax(json_str, "json", theme="monokai", background_color="default"))
                
        except Exception as e:
            console.print(f"[red]CLI Error: {e}[/red]")
        except KeyboardInterrupt:
            break

    client.close()

if __name__ == "__main__":
    main()
