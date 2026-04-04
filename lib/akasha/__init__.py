import os

db_dir = os.path.dirname(self.db_path)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir)