import os
from datetime import datetime

LOG_DIR = "output/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join(LOG_DIR, f"log_{datetime.now():%Y-%m-%d}.txt")
    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")  # also prints to GitHub Actions console
