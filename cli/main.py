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
        self.it = None  # 直近のハッシュキーを保持

    def sync_api(self):
        """APIからOpenAPI定義を取得し、コマンドを自動構成"""
        try:
            resp = httpx.get(f"{self.api_url}/openapi.json", timeout=5.0)
            spec = resp.json()
            self.commands = {} # Reset
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
            console.print(f"[red]API接続エラー: {e}\nUvicornが起動しているか確認してください。[/red]")
            return False

    def show_help(self, target=None):
        if not target:
            table = Table(title="Akashic Stack Commands", header_style="bold magenta")
            table.add_column("Command", style="cyan")
            table.add_column("Summary")
            for name, info in self.commands.items():
                table.add_row(name, info['summary'])
            console.print(table)
            console.print("\n[dim]Tips: 'help <command>' で詳細を表示できます。[/dim]")
        elif target in self.commands:
            info = self.commands[target]
            content = f"[yellow]Summary:[/yellow] {info['summary']}\n"
            content += f"[yellow]Description:[/yellow] {info['description']}\n"
            content += f"[yellow]Endpoint:[/yellow] {info['method']} {info['path']}"
            console.print(Panel(content, title=f"Command: {target}", expand=False))

    def execute(self, cmd_name, args):
        info = self.commands[cmd_name]
        url = f"{self.api_url}{info['path']}"
        
        # 1. パスパラメータの自動置換 ({key} があれば $it または第一引数を使用)
        if "{key}" in url:
            if not args and not self.it:
                console.print("[red]Error: キーが指定されておらず、$it も空です。[/red]")
                return
            key_val = args[0] if args else self.it
            url = url.format(key=key_val)
            args = args[1:] if args else []

        # 2. リクエストボディの構築
        payload = {}
        query_params = {}
        if info['method'] in ["POST", "PUT"]:
            val = " ".join(args)
            if cmd_name == "write": payload = {"content": val}
            elif cmd_name == "tag": payload = {"trait": val}
        elif info['method'] == "GET" and cmd_name == "find":
            query_params = {"q": ",".join(args)}

        # 3. リクエスト実行
        try:
            resp = httpx.request(info['method'], url, json=payload, params=query_params)
            data = resp.json()
            
            # 成功時に $it を更新
            if isinstance(data, dict) and "key" in data:
                self.it = data["key"]
                console.print(f"[bold yellow]>> $it updated: {self.it}[/bold yellow]")
            
            console.print_json(data=json.dumps(data))
        except Exception as e:
            console.print(f"[red]Execution error: {e}[/red]")

    def run(self):
        if not self.sync_api(): return
        
        # 補完候補の作成
        completer = WordCompleter(list(self.commands.keys()) + ["help", "exit", "clear", "sync"])
        session = PromptSession(completer=completer)
        
        console.print(Panel("[bold green]Akashic Stack Shell v0.1[/bold green]\nDynamic OpenAPI Sync: [cyan]Enabled[/cyan]"))
        
        while True:
            try:
                # プロンプトに現在の $it を表示
                it_label = f" [blue]($it:{self.it[:8]}...)[/blue]" if self.it else ""
                text = session.prompt(f"Stack{it_label} > ").strip()
                
                if not text: continue
                parts = text.split()
                cmd = parts[0]
                
                if cmd == "exit": break
                elif cmd == "clear": console.clear()
                elif cmd == "sync": 
                    if self.sync_api(): console.print("[green]API definitions re-synced.[/green]")
                elif cmd == "help": 
                    self.show_help(parts[1] if len(parts) > 1 else None)
                elif cmd in self.commands: 
                    self.execute(cmd, parts[1:])
                else: 
                    console.print(f"[red]Unknown command: {cmd}. Type 'help' to see available commands.[/red]")
            except (KeyboardInterrupt, EOFError): break

if __name__ == "__main__":
    # 引数でURL指定も可能
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    AkashicShell(target_url).run()
