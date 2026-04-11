import os, sys, json, subprocess, shlex
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class AkashaAdapter:
    def __init__(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["PYTHONPATH"] = root_dir
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "api.main", "--stdio"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env, cwd=root_dir
        )
        console.print(Panel("[bold cyan]Akashic Stack CLI v0.3.0[/bold cyan]", expand=False))

    def call(self, method, params=None):
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1}
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line: return {"error": "Engine disconnected"}
        resp = json.loads(line)
        return resp.get("result") if "result" in resp else resp.get("error")

def display_result(result):
    if not result: return console.print("[dim]Empty.[/dim]")
    if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
        table = Table(show_header=True, header_style="bold blue")
        for key in result[0].keys(): table.add_column(key)
        for item in result: table.add_row(*[str(v) for v in item.values()])
        console.print(table)
    else:
        console.print(result)

def main():
    adapter = AkashaAdapter()
    while True:
        try:
            line = input("\nAkasha> ").strip()
            if not line or line.lower() in ["exit", "quit"]: break
            parts = shlex.split(line)
            cmd = parts[0]
            params = {"client_id": "me"}

            if cmd == "write": params["text"] = parts[1]
            elif cmd == "list": params["limit"] = int(parts[1]) if len(parts) > 1 else 10
            elif cmd == "read": params["id"] = parts[1] if len(parts) > 1 else "$it"
            elif cmd == "affix":
                params["id"], params["trait"] = parts[1], parts[2]
            elif cmd == "set":
                params["sub"] = parts[1]
                if params["sub"] == "add":
                    params["name"], params["id"] = parts[2], (parts[3] if len(parts)>3 else "$it")
                else: params["name"] = parts[2] if len(parts)>2 else ""
            elif cmd == "help": pass
            
            display_result(adapter.call(cmd, params))
        except Exception as e: console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
