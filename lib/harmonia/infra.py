import os

class HarmoniaInfra:
    def __init__(self, root_path: str = "."):
        self.root_path = os.path.abspath(root_path)
        self.data_dir = os.path.join(self.root_path, "data")
        self.master_logs = os.path.join(self.root_path, "logs")
        self.domains_dir = os.path.join(self.root_path, "domains")

    def setup_system(self):
        """システム全体の基本構造を作成"""
        dirs = [self.data_dir, self.master_logs, self.domains_dir]
        for d in dirs:
            os.makedirs(d, exist_ok=True)
            # Gitで見失わないよう.gitkeepを配置
            with open(os.path.join(d, ".gitkeep"), "a"): pass
        return True

    def setup_domain(self, domain_id: str):
        """ドメイン個別のパーティションを作成"""
        domain_root = os.path.join(self.domains_dir, domain_id)
        sub_dirs = ["import", "export", "processed", "work", "logs", "config"]
        
        for sd in sub_dirs:
            path = os.path.join(domain_root, sd)
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, ".gitkeep"), "a"): pass
            
        return domain_root
