import os
import json
from logger import log

# ---------------- Paths ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_DIR = os.path.join(BASE_DIR, "output", "metadata")
INDEX_FILE = os.path.join(METADATA_DIR, "index.json")
ALL_POSTS_FILE = os.path.join(METADATA_DIR, "all_posts.json")

# ---------------- Ensure metadata folder exists ----------------
if not os.path.isdir(METADATA_DIR):
    raise RuntimeError(f"Metadata directory not found: {METADATA_DIR}")

# ---------------- Gather all JSON files ----------------
# Include all posts_*.json files (historical + new)
files = sorted(
    f for f in os.listdir(METADATA_DIR)
    if f.startswith("posts_") and f.endswith(".json")
)

if not files:
    raise RuntimeError("No post files found — index.json not written")

# ---------------- Merge all posts ----------------
all_posts = []
for f in files:
    path = os.path.join(METADATA_DIR, f)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
        if isinstance(data, list):
            all_posts.extend(data)

# Sort posts newest first by "date"
all_posts.sort(key=lambda p: p.get("date", ""), reverse=True)

# ---------------- Write index.json (list of all JSON files) ----------------
with open(INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(files, f, indent=2)

# ---------------- Write all_posts.json (merged data) ----------------
with open(ALL_POSTS_FILE, "w", encoding="utf-8") as f:
    json.dump(all_posts, f, indent=2)

# ---------------- Done ----------------
log(f"✅ index.json written to {INDEX_FILE}")
log(f"✅ al
