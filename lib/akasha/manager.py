import os, time, threading, queue, json
from lib.akasha.engine import AkashaEngine

class SessionInstance:
    """個体ごとの状態（メモリ上のコンテキスト）"""
    def __init__(self, client_id, db_path, mode="seeds"):
        self.client_id = client_id
        self.engine = AkashaEngine(db_path=db_path)
        self.it_key = None
        self.last_access = time.time()
        self.mode = mode

class AkashaManager:
    """マルチテナント・スリープ・共有キューの管理"""
    def __init__(self, base_dir="data/tenants", is_enterprise=True):
        self.base_dir = base_dir
        self.is_enterprise = is_enterprise
        self.active_sessions = {}
        self.shared_queue = queue.Queue()
        self.lock = threading.Lock()
        
        # 共有DB（BBS）への直列書き込みスレッド
        if is_enterprise:
            os.makedirs("data/shared", exist_ok=True)
            threading.Thread(target=self._shared_worker, daemon=True).start()

    def _shared_worker(self):
        """共有空間（BBS）への書き込みを一本化し競合を排除"""
        shared_engine = AkashaEngine(db_path="data/shared/bbs.db")
        while True:
            job = self.shared_queue.get()
            if job:
                shared_engine.commit(job['content'])
            self.shared_queue.task_done()

    def get_session(self, client_id="me"):
        with self.lock:
            cid = "me" if not self.is_enterprise else client_id
            if cid not in self.active_sessions:
                path = f"{self.base_dir}/{cid}/akasha.db"
                os.makedirs(os.path.dirname(path), exist_ok=True)
                self.active_sessions[cid] = SessionInstance(cid, path, "enterprise" if self.is_enterprise else "seeds")
            
            session = self.active_sessions[cid]
            session.last_access = time.time()
            return session

    def gc(self, timeout=300):
        """資源解放：放置されたセッションをメモリからパージ"""
        with self.lock:
            now = time.time()
            expired = [k for k, s in self.active_sessions.items() if now - s.last_access > timeout]
            for k in expired: del self.active_sessions[k]
