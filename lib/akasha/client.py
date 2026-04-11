import json, subprocess, sys, os, requests

class AkashaClient:
    """Akashaファミリー共通の通信プロトコル・レイヤー"""
    def __init__(self, mode="stdio", endpoint=None):
        self.mode = mode
        self.endpoint = endpoint
        self.proc = None
        
        if mode == "stdio":
            self._start_stdio()

    def _start_stdio(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        env = {**os.environ, "PYTHONPATH": root_dir}
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "api.main", "--stdio"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env, cwd=root_dir
        )

    def send(self, method, params=None):
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1}
        
        if self.mode == "stdio":
            self.proc.stdin.write(json.dumps(payload) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
            return json.loads(line) if line else {"error": "No response"}
        
        elif self.mode == "http":
            resp = requests.post(f"{self.endpoint}/rpc", json=payload)
            return resp.json()

    # MCPフレンドリーなショートカットメソッド
    def initialize(self): return self.send("initialize")
    def write(self, text): return self.send("write", {"text": text})
    def list_atoms(self, limit=10): return self.send("list", {"limit": limit})
