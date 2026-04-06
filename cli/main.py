import httpx
import sys
import json
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class AkashicShell:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.commands = {}
        self.it = None

    def sync_api(self):
        try:
            resp = httpx.get(f"{self.api_url}/openapi.json", timeout=5.0)
            spec = resp.json()
            self.commands = {}
            for path, methods in spec['paths'].items():
                for method, details in methods.items():
                    op_id = details.get('operationId')
                    if op_id:
                        self.commands[op_id] = {
                            "path": path, "method": method.upper(),
                            "summary": details.get('summary', ''),
                            "description": details.get('description', '')
                        }
            return True
        except Exception as e:
            console.print(f"[red]API Sync Error: {e}[/red]")
            return False

    def execute(self, cmd_name, args):
        info = self.commands[cmd_name]
        url_path = info['path']
        
        # パスパラメータの解決 ({key}, {name})
        if "{key}" in url_path:
            val = args[0] if args else self.it
            if not val:
                console.print("[red]Error: Key ($it) is missing.[/red]")
                return
            url_path = url_path.format(key=val)
            args = args[1:] if args else []
        
        if "{name}" in url_path:
            if not args:
                console.print("[red]Error: Set name is required.[/red]")
                return
            url_path = url_path.format(name=args[0])
            args = args[1:]

        url = f"{self.api_url}{url_path}"
        payload = {}
        if info['method'] in ["POST", "PUT"]:
            val = " ".join(args)
            if cmd_name == "write": payload = {"content": val}
            elif cmd_name == "tag": payload = {"trait": val}
            elif cmd_name == "set_create": payload = {"name": val}

        try:
            resp = httpx.request(info['method'], url, json=payload)
            # JSONパースエラーを防ぐ
            try:
                data = resp.json()
            except json.JSONDecodeError:
                data = {"status": resp.status_code, "text": resp.text}

            if isinstance(data, dict) and "key" in data:
                self.it = data["key"]
                console.print(f"[bold yellow]>> $it updated: {self.it}[/bold yellow]")
            
            console.print_json(data=json.dumps(data))
        except Exception as e:
            console.print(f"[red]Request Error: {e}[/red]")

    def run(self):
        if not self.sync_api(): return
        session = PromptSession(completer=WordCompleter(list(self.commands.keys()) + ["help", "exit", "sync"]))
        console.print(Panel("[bold green]Akashic Stack Shell v0.2[/bold green]\nDynamic Set Operations: [cyan]Enabled[/cyan]"))
        
        while True:
            try:
                label = f" [blue]($it:{self.it[:8]}...)[/blue]" if self.it else ""
                text = session.prompt(f"Stack{label} > ").strip()
                if not text: continue
                parts = text.split()
                cmd = parts[0]
                if cmd == "exit": break
                elif cmd == "sync": self.sync_api()
                elif cmd in self.commands: self.execute(cmd, parts[1:])
                else: console.print(f"[red]Unknown: {cmd}[/red]")
            except (KeyboardInterrupt, EOFError): break

if __name__ == "__main__":
    AkashicShell().run()
