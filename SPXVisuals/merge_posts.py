import json
import glob
import os
from logger import log

METADATA_DIR = "output/metadata"
OUTPUT_FILE = os.path.join(METADATA_DIR, "posts.json")

os.makedirs(METADATA_DIR, exist_ok=True)


def build_text(p):
    if p["type"] == "ma":
        return f"{p['ticker']} moving averages"
    if p["type"] == "normalized":
        return "Normalized price performance"
    if p["type"] == "gainers_losers":
        return "S&P 500 leaders & laggards"
    if p["type"] == "marketcap":
        return "Market cap distribution"
    if p["type"] == "pe":
        return "Valuation multiples"
    return ""


files = sorted(glob.glob(os.path.join(METADATA_DIR, "posts_*.json")))
all_posts = []

for f in files:
    date_str = os.path.basename(f).replace("posts_", "").replace(".json", "")

    with open(f, "r") as fh:
        daily_posts = json.load(fh)

    if not isinstance(daily_posts, list):
        continue

    for p in daily_posts:
        images = p.get("images")
        if not images:
            continue

        hashtags = [f"#{p['type'].upper()}"]

        if "timeframe" in p:
            hashtags.append(f"#{p['timeframe']}")
        elif "label" in p:
            hashtags.append(f"#{p['label']}")

        all_posts.append({
            "date": date_str,
            "hashtags": hashtags,
            "text": build_text(p),
            "images": images,
            "url": None
        })

# newest first
all_posts.sort(key=lambda p: p["date"], reverse=True)

with open(OUTPUT_FILE, "w") as out:
    json.dump(all_posts, out, indent=2)

log(f"Wrote {len(all_posts)} posts to {OUTPUT_FILE}")
