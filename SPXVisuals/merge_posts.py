import json, glob, os

files = sorted(glob.glob("SPXVisuals/output/metadata/posts_*.json"))
all_posts = []

for f in files:
    if os.path.getsize(f) > 0:  # skip empty files
        try:
            with open(f) as fh:
                all_posts.extend(json.load(fh))
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON file: {f}")

with open("SPXVisuals/output/metadata/posts.json", "w") as out:
    json.dump(all_posts, out, indent=2)
