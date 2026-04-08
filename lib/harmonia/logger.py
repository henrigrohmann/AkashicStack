import logging
import os

def get_harmonia_logger(domain_id: str, domain_root: str, master_log_path: str):
    logger = logging.getLogger(f"Harmonia.{domain_id}")
    logger.setLevel(logging.DEBUG)
    
    # 既存のハンドラをクリア（二重出力を防止）
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    # 1. Master System Log (運営側)
    master_handler = logging.FileHandler(master_log_path)
    master_handler.setFormatter(formatter)
    master_handler.setLevel(logging.INFO)
    logger.addHandler(master_handler)

    # 2. Domain Activity Log (クライアント側)
    domain_log_path = os.path.join(domain_root, "logs", "activity.log")
    domain_handler = logging.FileHandler(domain_log_path)
    domain_handler.setFormatter(formatter)
    domain_handler.setLevel(logging.DEBUG)
    logger.addHandler(domain_handler)

    # 3. Console Output (デバッグ用)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
