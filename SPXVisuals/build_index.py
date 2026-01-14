import os
import json

# ===== CONFIGURE THIS ONCE =====
SITE_REPO_PATH = "../site-repo"   # relative to generator repo
METADATA_SUBDIR = "output/metadata"
# ===============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_METADATA_DIR = os.path.abspath(
    os.path.join(BASE_DIR, SITE_REPO_PATH, METADATA_SUBDIR)
)

if not os.path.isdir(SITE_METADATA_DIR):
    raise RuntimeError(
        f"Metadata directory not found: {SITE_METADATA_DIR}"
    )

files = sorted(
    f for f in os.listdir(SITE_METADATA_DIR)
    if f.startswith("posts_") and f.endswith(".json")
)

if not files:
    raise RuntimeError("No post files found — index.json not written")

index_path = os.path.join(SITE_METADATA_DIR, "index.json")

with open(index_path, "w", encoding="utf-8") as f:
    json.dump(files, f, indent=2)

print(f"index.json written to {index_path}")
print(f"{len(files)} files indexed:")
for f in files:
    print(" -", f)

