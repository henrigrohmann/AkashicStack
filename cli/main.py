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
        """APIのOpenAPI仕様から動的にコマンドを同期する"""
        try:
            resp = httpx.get(f"{self.api_url}/openapi.json", timeout=5.0)
            spec = resp.json()
            self.commands = {}
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
            console.print(f"[red]API Sync Error: {e}[/red]")
            return False

    def execute(self, cmd_name, args):
        """動的コマンドの実行ロジック"""
        info = self.commands[cmd_name]
        url_path = info['path']
        method = info['method']
        
        # 1. パスパラメータの解決
        # {name} (Set名) の解決を優先
        if "{name}" in url_path:
            if not args:
                console.print("[red]Error: Set name is required.[/red]")
                return
            url_path = url_path.format(name=args[0])
            args = args[1:] # 最初の引数を消費

        # {key} (個別Chunk) の解決
        if "{key}" in url_path:
            val = args[0] if args else self.it
            if not val:
                console.print("[red]Error: Key ($it) is missing.[/red]")
                return
            url_path = url_path.format(key=val)
            args = args[1:] if args else []

        url = f"{self.api_url}{url_path}"
        
        # 2. ペイロードとクエリパラメータの構築
        params = {}
        payload = {}
        
        if method in ["POST", "PUT"]:
            if cmd_name == "write":
                payload = {"content": " ".join(args)}
            elif cmd_name == "tag":
                payload = {"trait": " ".join(args)}
            elif cmd_name == "set_create":
                payload = {"name": args[0] if args else ""}
            elif cmd_name == "set_add":
                # $it または 第一引数を key としてクエリパラメータで送る
                key_val = args[0] if args else self.it
                params = {"key": key_val}

        try:
            # APIリクエストの実行
            resp = httpx.request(method, url, json=payload, params=params)
            
            # ステータスコードに応じたエラー表示
            if resp.is_error:
                console.print(f"[red]Status: {resp.status_code}[/red]")
            
            try:
                data = resp.json()
            except json.JSONDecodeError:
                data = {"text": resp.text}

            # $it (コンテキスト) の更新ロジック
            if isinstance(data, dict):
                new_key = data.get("key")
                if new_key and new_key != "None":
                    self.it = new_key
                    console.print(f"[bold yellow]>> $it updated: {self.it[:8]}...[/bold yellow]")
            
            console.print_json(data=json.dumps(data))
            
        except Exception as e:
            console.print(f"[red]Request Error: {e}[/red]")

    def run(self):
        """メインループの実行"""
        if not self.sync_api():
            console.print("[yellow]Retrying API sync... Make sure uvicorn is running.[/yellow]")
            if not self.sync_api(): return

        # コマンド補完の設定
        session = PromptSession(
            completer=WordCompleter(list(self.commands.keys()) + ["help", "exit", "sync"])
        )
        
        console.print(Panel(
            "[bold green]Akashic Stack Shell v0.2[/bold green]\n"
            "Dynamic Set Operations: [cyan]Enabled[/cyan]"
        ))
        
        while True:
            try:
                # プロンプトに現在の$itを表示
                label = f" [blue]($it:{self.it[:8]}...)[/blue]" if self.it else ""
                text = session.prompt(f"Stack{label} > ").strip()
                
                if not text: continue
                parts = text.split()
                cmd = parts[0]
                
                if cmd == "exit":
                    break
                elif cmd == "sync":
                    self.sync_api()
                elif cmd in self.commands:
                    self.execute(cmd, parts[1:])
                else:
                    console.print(f"[red]Unknown command: {cmd}[/red]")
                    
            except (KeyboardInterrupt, EOFError):
                break

if __name__ == "__main__":
    AkashicShell().run()
