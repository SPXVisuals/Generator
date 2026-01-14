import os
import json

# Use script location as base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_DIR = os.path.join(BASE_DIR, "output", "metadata")

if not os.path.isdir(METADATA_DIR):
    raise RuntimeError(f"Metadata directory not found: {METADATA_DIR}")

# Index all JSON files except index.json itself
files = sorted(
    f for f in os.listdir(METADATA_DIR)
    if f.startswith("posts_") and f.endswith(".json")
)

if not files:
    raise RuntimeError("No post files found — index.json not written")

index_path = os.path.join(METADATA_DIR, "index.json")

with open(index_path, "w", encoding="utf-8") as f:
    json.dump(files, f, indent=2)

print(f"index.json written to {index_path}")
print(f"{len(files)} files indexed:")
for f in files:
    print(" -", f)
