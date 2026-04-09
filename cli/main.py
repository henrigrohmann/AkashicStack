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
    def __init__(self, mode="stdio"):
        self.mode = mode
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.proc = subprocess.Popen(
            [sys.executable, "api/main.py", "--stdio"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr,
            text=True, bufsize=1, env=env
        )

    def call(self, cmd, args=[]):
        try:
            payload = json.dumps({"cmd": cmd, "args": args})
            self.proc.stdin.write(payload + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
            return json.loads(line) if line else {"error": "No response"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

def display_result(result):
    if isinstance(result, list):
        if not result:
            console.print("[yellow]Empty result.[/yellow]")
            return
        table = Table(show_header=True, header_style="bold blue")
        # カラム名の動的取得
        for key in result[0].keys():
            table.add_column(key)
        for item in result:
            table.add_row(*[str(v) for v in item.values()])
        console.print(table)
    else:
        console.print(result)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true", default=True)
    cli_args = parser.parse_args()

    adapter = AkashaAdapter(mode="stdio")
    console.print(Panel("[bold cyan]Akashic Stack CLI v0.2.1[/bold cyan]\n[dim]Dynamic Identity & Environment Verified.[/dim]", expand=False))

    while True:
        try:
            line = input("Akasha> ").strip()
            if not line: continue
            if line.lower() in ["exit", "quit"]: break
            
            parts = line.split()
            cmd, args = parts[0], parts[1:]
            
            result = adapter.call(cmd, args)
            
            if cmd == "help" and "commands" in result:
                # ヘルプ表示用
                table = Table(title="Akashic Commands", header_style="bold magenta")
                table.add_column("Command")
                table.add_column("Description")
                for c, d in result["commands"].items(): table.add_row(c, d)
                console.print(table)
            else:
                display_result(result)
            
        except (KeyboardInterrupt, EOFError): break
        except Exception as e: console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
