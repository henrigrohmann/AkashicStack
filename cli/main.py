import os, sys, json, subprocess, argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class AkashaAdapter:
    def __init__(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.proc = subprocess.Popen(
            [sys.executable, "api/main.py", "--stdio"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr,
            text=True, bufsize=1, env=env
        )

    def call(self, cmd, args=[]):
        try:
            self.proc.stdin.write(json.dumps({"cmd": cmd, "args": args}) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
            return json.loads(line) if line else {"error": "no response"}
        except Exception as e: return {"error": str(e)}

def main():
    adapter = AkashaAdapter()
    console.print(Panel("[bold cyan]Akashic Stack CLI v0.2.2[/bold cyan]\n[dim]Serial ID & $it enabled. Use '0' or '$it' for keys.[/dim]", expand=False))

    while True:
        try:
            line = input("\nAkasha> ").strip()
            if not line: continue
            if line.lower() in ["exit", "quit"]: break
            
            parts = line.split()
            cmd, args = parts[0], parts[1:]
            result = adapter.call(cmd, args)
            
            if isinstance(result, list):
                table = Table(show_header=True, header_style="bold blue")
                table.add_column("ID", style="dim")
                for k in result[0].keys(): table.add_column(k)
                for idx, item in enumerate(result):
                    table.add_row(str(idx), *[str(v) for v in item.values()])
                console.print(table)
            else:
                console.print(result)
        except (KeyboardInterrupt, EOFError): break
        except Exception as e: console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
