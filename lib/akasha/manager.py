from .engine import AkashaEngine, NucleusEngine

class AkashaSession:
    def __init__(self, client_id, role="cell"):
        self.client_id = client_id
        self.role = role
        self.it_key = None
        
        # 1. Nucleus (金庫)
        self.nucleus = NucleusEngine("data/central/nucleus.db")
        # 2. Cortex (皮質 - 永続)
        self.global_cortex = AkashaEngine("data/central/g_cortex.db")
        self.local_cortex  = AkashaEngine(f"data/cells/{client_id}/l_cortex.db")
        # 3. Hippocampus (短期記憶 - 揮発フラグ付与)
        self.global_hippo  = AkashaEngine("data/temp/g_hippo.db", is_volatile=True)
        self.local_hippo   = AkashaEngine(f"data/temp/{client_id}_hippo.db", is_volatile=True)

class AkashaManager:
    def __init__(self):
        self.sessions = {}
        self.master_nucleus = NucleusEngine("data/central/nucleus.db")

    def authenticate(self, client_id, secret):
        auth_data = self.master_nucleus.vault_retrieve("auth", client_id)
        if auth_data and auth_data.get("secret") == secret:
            return auth_data.get("role", "cell")
        return None

    def register(self, client_id, secret, role="cell"):
        if self.master_nucleus.vault_retrieve("auth", client_id):
            return False
        self.master_nucleus.vault_store("auth", client_id, {"secret": secret, "role": role})
        return True

    def get_session(self, client_id, role="cell"):
        if client_id not in self.sessions:
            self.sessions[client_id] = AkashaSession(client_id, role)
        return self.sessions[client_id]
