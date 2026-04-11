import json
import subprocess
import sys
import os
import requests

class AkashaClient:
    """
    Akashaプロトコル・アダプター。
    stdio（子プロセス）とHTTP（ネットワーク）の両方を隠蔽して同じメソッドで提供する。
    """
    def __init__(self, mode="stdio", endpoint=None):
        self.mode = mode
        self.endpoint = endpoint
        self.proc = None
        
        if mode == "stdio":
            self._start_stdio_process()

    def _start_stdio_process(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        env = {**os.environ, "PYTHONPATH": root_dir}
        # 内部で api.main を --stdio モードで起動
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "api.main", "--stdio"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env, cwd=root_dir
        )

    def call(self, method, params=None):
        """JSON-RPC / MCP 形式でリクエストを送信"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1
        }

        if self.mode == "stdio":
            self.proc.stdin.write(json.dumps(payload) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
            return json.loads(line) if line else {"error": "No response from stdio"}
        
        elif self.mode == "http":
            try:
                # endpoint は http://localhost:8000 等を想定
                resp = requests.post(f"{self.endpoint}/rpc", json=payload)
                return resp.json()
            except Exception as e:
                return {"error": f"HTTP Connection failed: {str(e)}"}

    def close(self):
        if self.proc:
            self.proc.terminate()
