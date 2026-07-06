import os
import json
import sys
from datetime import datetime

mode = sys.argv[1].upper() if len(sys.argv) > 1 else "PM"
RUN_DATE = datetime.now().strftime("%Y-%m-%d")

def build_tweet_text(post):
    hashtags = ["#SPXVisuals"]

    if post.get("ticker"):
        hashtags.append(f"${post['ticker']}")
        hashtags.append(f"#{post['ticker']}")
    else:
        hashtags.append("$SPY")

    hashtags.extend([
        "#SPY", "#SPX", "#SP500", "#SAndP500",
        "#Equities", "#Stocks", "#Market",
        "#StockMarket", "#Investing"
    ])

    hashtags_text = " ".join(hashtags)

    if post["type"] == "ma":
        return f"{post['ticker']} SMA & EMA Charts 📈 {hashtags_text}"

    elif post["type"] == "normalized":
        return f"Normalized Price Charts For The 40 Largest S&P 500 Components 📈 {hashtags_text}"

    elif post["type"] == "marketcap":
        return f"Market Capitalization Distribution Charts 📊 {hashtags_text}"

    elif post["type"] == "volume":
        return f"Volume Distribution Charts 📊 {hashtags_text}"

    elif post["type"] == "pe":
        return f"P/E Ratio Charts 📊 {hashtags_text}"

    elif post["type"] == "gainers_losers":
        return f"S&P 500 Leaders & Laggards 📋 {hashtags_text}"

    return hashtags_text


def update_metadata():
    meta_path = f"output/metadata/posts_{RUN_DATE}_{mode.lower()}.json"

    if not os.path.exists(meta_path):
        print(f"Metadata file not found: {meta_path}")
        return

    with open(meta_path, "r") as f:
        posts = json.load(f)

    for post in posts:
        post["tweet_text"] = build_tweet_text(post)

        # Blank URL so website hides the X button
        post["tweet_url"] = ""

        # Optional marker
        post["tweet_id"] = "website-only"

    with open(meta_path, "w") as f:
        json.dump(posts, f, indent=2)

    print(f"Updated {len(posts)} posts for website publishing")


if __name__ == "__main__":
    update_metadata()
