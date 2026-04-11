import os, sys, json, subprocess, argparse, shlex
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class AkashaAdapter:
    def __init__(self):
        # パス設定: プロジェクトルートをPYTHONPATHに追加
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["PYTHONPATH"] = root_dir
        
        # 起動コマンドの修正:
        # 1. sys.executable を使用
        # 2. -u でバッファリングを無効化
        # 3. -m api.main でモジュールとして起動（インポートエラー防止）
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "api.main", "--stdio"],
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True, 
            bufsize=1, 
            env=env,
            cwd=root_dir # カレントディレクトリをルートに固定
        )
        
        # 起動直後のエラーチェック
        # stderrに何か出ていないか確認（もしエラーがあればここで表示される）
        console.print(Panel(f"[bold cyan]Akashic Stack CLI v0.2.3[/bold cyan]", expand=False))

    def call(self, method, params=None):
        if params is None: params = {}
        # JSON-RPC 2.0 形式に変換
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        try:
            self.proc.stdin.write(json.dumps(payload) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
            
            if not line:
                #  stderrからエラー詳細を取得して表示
                err_log = self.proc.stderr.readline()
                return {"error": f"Engine disconnected. Log: {err_log}"}
                
            resp = json.loads(line)
            # JSON-RPCの結果またはエラーを返す
            return resp.get("result") if "result" in resp else resp.get("error")
        except Exception as e: 
            return {"error": str(e)}

def display_result(result):
    if result is None:
        console.print("[yellow]Empty result.[/yellow]")
        return
        
    if isinstance(result, list) and len(result) > 0:
        table = Table(show_header=True, header_style="bold blue")
        # keyが存在する場合のみTable表示
        if isinstance(result[0], dict) and 'key' in result[0]:
            for key in result[0].keys(): table.add_column(key)
            for item in result:
                table.add_row(*[str(v) for v in item.values()])
            console.print(table)
        else:
            console.print(result)
    else:
        # エラー表示などの装飾
        if isinstance(result, dict) and "message" in result:
            console.print(f"[red]Error: {result['message']}[/red]")
        else:
            console.print(result)

def main():
    adapter = AkashaAdapter()

    while True:
        try:
            line = input("\nAkasha> ").strip()
            if not line: continue
            if line.lower() in ["exit", "quit"]: break
            
            parts = shlex.split(line)
            cmd = parts[0]
            
            # 入力引数を params 形式に変換する簡易ロジック
            # write "text content" -> method="write", params={"text": "text content"}
            params = {}
            if cmd == "write" and len(parts) > 1:
                params = {"text": parts[1]}
            elif cmd == "list" and len(parts) > 1:
                params = {"limit": int(parts[1])}
            elif cmd == "read" and len(parts) > 1:
                params = {"id": parts[1]}
            
            # client_id はとりあえず "me" 固定（テスト用）
            params["client_id"] = "me"
            
            result = adapter.call(cmd, params)
            display_result(result)
                
        except (KeyboardInterrupt, EOFError): break
        except Exception as e: console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
