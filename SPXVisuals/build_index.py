import os
import json

# ---------------- Paths ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_DIR = os.path.join(BASE_DIR, "output", "metadata")
INDEX_FILE = os.path.join(METADATA_DIR, "index.json")
ALL_POSTS_FILE = os.path.join(METADATA_DIR, "all_posts.json")

if not os.path.isdir(METADATA_DIR):
    raise RuntimeError(f"Metadata directory not found: {METADATA_DIR}")

# ---------------- Gather all JSON files ----------------
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

# Sort posts newest first by "date" key
all_posts.sort(key=lambda p: p.get("date", ""), reverse=True)

# ---------------- Write index.json ----------------
with open(INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(files, f, indent=2)

# ---------------- Write all_posts.json ----------------
with open(ALL_POSTS_FILE, "w", encoding="utf-8") as f:
    json.dump(all_posts, f, indent=2)

# ---------------- Done ----------------
print(f"✅ index.json written to {INDEX_FILE}")
print(f"✅ all_posts.json written to {ALL_POSTS_FILE}")
print(f"📄 {len(files)} JSON files indexed, {len(all_posts)} total posts")
