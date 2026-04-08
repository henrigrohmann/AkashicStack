from lib.harmonia.infra import HarmoniaInfra
from lib.harmonia.logger import get_harmonia_logger
import os

def main():
    infra = HarmoniaInfra()
    
    # 1. 土木工事
    print("Initializing System Infrastructure...")
    infra.setup_system()
    
    domain_id = "default"
    domain_root = infra.setup_domain(domain_id)
    print(f"Domain '{domain_id}' environment set up at {domain_root}")

    # 2. ログ疎通テスト
    master_log_path = os.path.join(infra.master_logs, "master.log")
    logger = get_harmonia_logger(domain_id, domain_root, master_log_path)
    
    logger.info("System Infrastructure Check: OK")
    logger.debug(f"Domain '{domain_id}' logging initialized.")
    print("Log check completed. See logs/master.log and domains/default/logs/activity.log")

if __name__ == "__main__":
    main()
