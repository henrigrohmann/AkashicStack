import os, sys, json, subprocess, argparse, shlex
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
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, # stderrもキャプチャ
            text=True, bufsize=1, env=env
        )
        # エンジンが起動するまで少し待つか、最初のメッセージを読み飛ばす
        init_log = self.proc.stderr.readline() 
        # パネルの表示をここで行う
        console.print(Panel(f"[bold cyan]Akashic Stack CLI v0.2.3[/bold cyan]\n[dim]{init_log.strip()}[/dim]", expand=False))

    def call(self, cmd, args=[]):
        try:
            self.proc.stdin.write(json.dumps({"cmd": cmd, "args": args}) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
            return json.loads(line) if line else {"error": "No response"}
        except Exception as e: return {"error": str(e)}

def display_result(result):
    # (前回と同じ: listの場合はTable表示、それ以外はJSON表示)
    if isinstance(result, list) and len(result) > 0 and 'key' in result[0]:
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("ID", style="dim")
        for key in result[0].keys(): table.add_column(key)
        for idx, item in enumerate(result):
            table.add_row(str(idx), *[str(v) for v in item.values()])
        console.print(table)
    else:
        console.print(result)

def main():
    adapter = AkashaAdapter()

    while True:
        try:
            # プロンプトの前に改行を入れ、入力待ちを明確にする
            line = input("\nAkasha> ").strip()
            if not line: continue
            if line.lower() in ["exit", "quit"]: break
            
            # shlexを使って引用符を考慮した分割を行う
            parts = shlex.split(line)
            cmd, args = parts[0], parts[1:]
            
            result = adapter.call(cmd, args)
            display_result(result)
                
        except (KeyboardInterrupt, EOFError): break
        except Exception as e: console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
