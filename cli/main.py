import os
import sys
import json
import subprocess
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class AkashaAdapter:
    def __init__(self):
        env = os.environ.copy()
        # lib へのパスを確実に通す
        env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.proc = subprocess.Popen(
            [sys.executable, "api/main.py", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr, # エンジンの内部ログ(stderr)をそのまま表示
            text=True,
            bufsize=1,
            env=env
        )

    def call(self, cmd, args=[]):
        try:
            payload = json.dumps({"cmd": cmd, "args": args})
            self.proc.stdin.write(payload + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
            return json.loads(line) if line else {"error": "No response from engine"}
        except Exception as e:
            return {"error": str(e)}

def display_result(result):
    if isinstance(result, list):
        if not result:
            console.print("[yellow]Empty result.[/yellow]")
            return
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("ID", style="dim") # シリアル番号
        for key in result[0].keys():
            table.add_column(key)
        
        for idx, item in enumerate(result):
            # valuesを文字列化して追加
            table.add_row(str(idx), *[str(v) for v in item.values()])
        console.print(table)
    else:
        console.print(result)

def main():
    # 1. 接続
    adapter = AkashaAdapter()
    
    # 2. 起動メッセージ (プロンプトの前に出す)
    console.print(Panel(
        "[bold cyan]Akashic Stack CLI v0.2.2[/bold cyan]\n"
        "[dim]Serial ID (0, 1...) & $it enabled. Prompt fixed.[/dim]", 
        expand=False
    ))

    # 3. メインループ
    while True:
        try:
            # 入力待ち (改行を挟んでプロンプトを独立させる)
            line = input("\nAkasha> ").strip()
            if not line: continue
            if line.lower() in ["exit", "quit"]: break
            
            parts = line.split()
            cmd, args = parts[0], parts[1:]
            
            result = adapter.call(cmd, args)
            
            if cmd == "help" and "commands" in result:
                table = Table(title="Available Commands", header_style="bold magenta")
                table.add_column("Command")
                table.add_column("Usage")
                for c, u in result["commands"].items():
                    table.add_row(c, u)
                console.print(table)
            else:
                display_result(result)
                
        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
