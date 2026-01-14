import os, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_DIR = os.path.join(BASE_DIR, "output", "metadata")

files = sorted(
    f for f in os.listdir(METADATA_DIR)
    if f.startswith("posts_") and f.endswith(".json")
)

with open(os.path.join(METADATA_DIR, "index.json"), "w") as f:
    json.dump(files, f, indent=2)
