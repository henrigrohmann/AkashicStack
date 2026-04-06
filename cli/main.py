import httpx
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json

console = Console()

class AkashicShell:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.commands = {}
        self.it = None  # 直近のハッシュを保持

    def sync_api(self):
        """OpenAPI定義をフェッチしてコマンドを自動構成"""
        try:
            resp = httpx.get(f"{self.api_url}/openapi.json")
            spec = resp.json()
            for path, methods in spec['paths'].items():
                for method, details in methods.items():
                    op_id = details.get('operationId')
                    if op_id:
                        self.commands[op_id] = {
                            "path": path,
                            "method": method.upper(),
                            "summary": details.get('summary', ''),
                            "description": details.get('description', '')
                        }
            return True
        except Exception as e:
            console.print(f"[red]API接続エラー: {e}[/red]")
            return False

    def show_help(self, target=None):
        if not target:
            table = Table(title="Akashic Stack Commands", header_style="bold magenta")
            table.add_column("Command", style="cyan")
            table.add_column("Summary")
            for name, info in self.commands.items():
                table.add_row(name, info['summary'])
            console.print(table)
        elif target in self.commands:
            info = self.commands[target]
            console.print(Panel(f"[bold]{target}[/bold]\n\n{info['summary']}\n{info['description']}", title="Command Detail"))

    def execute(self, cmd_name, args):
        info = self.commands[cmd_name]
        path = info['path']
        url = f"{self.api_url}{path}"
        
        # 1. パスパラメータの自動置換 ({key} があれば $it または引数から充填)
        if "{key}" in url:
            if not args and not self.it:
                console.print("[red]Error: キーが指定されておらず、$it も空です。[/red]")
                return
            key_to_use = args[0] if args else self.it
            url = url.format(key=key_to_use)
            args = args[1:] if args else []

        # 2. ボディデータの構築 (単純化のため)
        payload = {}
        if info['method'] in ["POST", "PUT"]:
            content = " ".join(args)
            if cmd_name == "write": payload = {"content": content}
            elif cmd_name == "tag": payload = {"trait": content}

        # 3. API実行
        try:
            resp = httpx.request(info['method'], url, json=payload)
            data = resp.json()
            
            # $it の更新
            if isinstance(data, dict) and "key" in data:
                self.it = data["key"]
                console.print(f"[yellow]>> $it updated: {self.it}[/yellow]")
            
            console.print_json(data=data)
        except Exception as e:
            console.print(f"[red]Execution error: {e}[/red]")

    def run(self):
        if not self.sync_api(): return
        
        completer = WordCompleter(list(self.commands.keys()) + ["help", "exit", "clear", "sync"])
        session = PromptSession(completer=completer)
        
        console.print(Panel("[bold green]Akashic Stack Shell[/bold green]\nAPI definitions synchronized. Type 'help' to see commands."))
        
        while True:
            try:
                it_label = f" [blue]($it:{self.it[:8]}...)[/blue]" if self.it else ""
                text = session.prompt(f"Stack{it_label} > ").strip()
                if not text: continue
                
                parts = text.split()
                cmd = parts[0]
                
                if cmd == "exit": break
                elif cmd == "clear": console.clear()
                elif cmd == "sync": self.sync_api(); console.print("[green]API synced.[/green]")
                elif cmd == "help": self.show_help(parts[1] if len(parts) > 1 else None)
                elif cmd in self.commands: self.execute(cmd, parts[1:])
                else: console.print(f"[red]Unknown command: {cmd}[/red]")
            except (KeyboardInterrupt, EOFError): break

if __name__ == "__main__":
    AkashicShell().run()
