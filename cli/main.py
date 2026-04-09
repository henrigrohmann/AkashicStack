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
        if mode == "stdio":
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

def display_help(commands):
    table = Table(title="Akashic Commands", show_header=True, header_style="bold magenta")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    for cmd, desc in commands.items():
        table.add_row(cmd, desc)
    console.print(table)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true", default=True)
    cli_args = parser.parse_args()

    adapter = AkashaAdapter(mode="stdio")
    console.print(Panel("[bold cyan]Akashic Stack CLI v0.2.1[/bold cyan]\n[dim]Ready for deployment test.[/dim]", expand=False))

    while True:
        try:
            line = input("Akasha> ").strip()
            if not line: continue
            if line.lower() in ["exit", "quit"]: break
            
            parts = line.split()
            cmd, args = parts[0], parts[1:]
            
            result = adapter.call(cmd, args)
            
            if cmd == "help" and "commands" in result:
                display_help(result["commands"])
            elif isinstance(result, list): # 一覧表示系
                table = Table(show_header=True, header_style="bold blue")
                if len(result) > 0:
                    for key in result[0].keys(): table.add_column(key)
                    for item in result: table.add_row(*[str(v) for v in item.values()])
                    console.print(table)
                else:
                    console.print("[yellow]Empty result.[/yellow]")
            else:
                console.print(result)
            
        except (KeyboardInterrupt, EOFError): break
        except Exception as e: console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
