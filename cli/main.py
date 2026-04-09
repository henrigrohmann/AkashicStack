import sys
import json
import subprocess
import httpx
import argparse
from rich.console import Console
from rich.table import Table

console = Console()

class AkashaAdapter:
    def __init__(self, mode="http", url="http://localhost:8000"):
        self.mode = mode
        self.url = url
        self.proc = None
        
        if mode == "stdio":
            # APIを子プロセスとして起動 (API側の--stdioフラグを立てる)
            self.proc = subprocess.Popen(
                [sys.executable, "api/main.py", "--stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=sys.stderr, # エラーはそのまま表示
                text=True,
                bufsize=1
            )

    def call(self, cmd, args=[]):
        if self.mode == "stdio":
            payload = json.dumps({"cmd": cmd, "args": args})
            self.proc.stdin.write(payload + "\n")
            return json.loads(self.proc.stdout.readline())
        else:
            # 従来のHTTP通信
            try:
                if cmd == "write":
                    res = httpx.post(f"{self.url}/write", json={"content": args[0]})
                elif cmd == "affix":
                    res = httpx.post(f"{self.url}/affix/{args[0]}", json={"trait": args[1]})
                return res.json()
            except Exception as e:
                return {"status": "error", "message": str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true", help="Connect via stdio pipe")
    cli_args = parser.parse_args()

    mode = "stdio" if cli_args.stdio else "http"
    adapter = AkashaAdapter(mode=mode)
    
    console.print(f"[bold cyan]Akashic Stack CLI[/bold cyan] (Mode: [yellow]{mode}[/yellow])")
    console.print("Type 'exit' to quit.\n")

    while True:
        try:
            line = input("Akasha> ").strip()
            if not line: continue
            if line.lower() == "exit": break
            
            parts = line.split()
            cmd, args = parts[0], parts[1:]
            
            result = adapter.call(cmd, args)
            console.print(result)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
