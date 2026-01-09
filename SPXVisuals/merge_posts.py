import json
import glob
import os

METADATA_DIR = "SPXVisuals/output/metadata"
OUTPUT_FILE = os.path.join(METADATA_DIR, "posts.json")

# Ensure output directory exists
os.makedirs(METADATA_DIR, exist_ok=True)

files = sorted(glob.glob(os.path.join(METADATA_DIR, "posts_*.json")))
all_posts = []

if not files:
    print("No posts_*.json files found. Writing empty posts.json.")
else:
    for f in files:
        if os.path.getsize(f) == 0:
            print(f"Skipping empty file: {f}")
            continue

        try:
            with open(f, "r") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    all_posts.extend(data)
                else:
                    print(f"Skipping non-list JSON file: {f}")
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON file: {f}")

with open(OUTPUT_FILE, "w") as out:
    json.dump(all_posts, out, indent=2)

print(f"Wrote {len(all_posts)} posts to {OUTPUT_FILE}")
