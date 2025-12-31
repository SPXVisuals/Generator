import os
import json
from datetime import datetime
from logger import log
import tweepy

# ---------------- Build tweet text ----------------
def build_tweet_text(post):
    hashtags = ["#SPXVisuals"]  # Always first

    if post.get("ticker"):
        hashtags.append(f"#{post['ticker']}")

    hashtags.extend([
        "#SPX", "#S&P500", "#SP500", "#SAndP500",
        "#Equities", "#Stocks", "#Market", "#StockMarket", "#Investing"
    ])

    type_tag_map = {
        "ma": "#SMA #EMA",
        "normalized": "#PriceChart",
        "marketcap": "#MarketCap",
        "pe": "#PE"
    }
    hashtags.append(type_tag_map.get(post["type"], ""))
    hashtags_text = " ".join(hashtags)

    timeframe_text, range_text = "", ""

    if post["type"] == "ma" and post["images"]:
        fname = os.path.basename(post["images"][0])
        if "_" in fname:
            timeframe = fname.split("_")[-1].replace(".png", "")
            timeframe_text = timeframe
    elif post["type"] == "normalized" and post["images"]:
        fname = os.path.basename(post["images"][0])
        timeframe_text = fname.split("_")[0]
        idx_num = int(fname.split("_")[1].split(".")[0])
        ranges = ["#1–#10", "#11–#20", "#21–#30", "#31–#40", "#41–#50"]
        range_text = ranges[idx_num] if idx_num < len(ranges) else ""
    elif post["type"] == "marketcap" and post["images"]:
        fname = os.path.basename(post["images"][0])
        if "1_10" in fname:
            range_text = "#1–#10"
        elif "11_25" in fname:
            range_text = "#11–#25"
        elif "26_50" in fname:
            range_text = "#26–#50"

    # Build text per type
    if post["type"] == "ma":
        return f"{timeframe_text} - {post['ticker']} SMA & EMA charts 📈 {hashtags_text}"
    elif post["type"] == "normalized":
        return f"{timeframe_text} - Normalized price chart for {range_text} Largest S&P 500 Index Components 📈 {hashtags_text}"
    elif post["type"] == "marketcap":
        return f"Market capitalization distribution chart for {range_text} Largest S&P 500 Index Components 🥧 {hashtags_text}"
    elif post["type"] == "pe":
        pe_type = "Trailing" if "trailing" in post.get("images", [""])[0] else "Forward"
        return f"{pe_type} P/E chart for the 50 Largest S&P 500 stocks 📊 {hashtags_text}"
    else:
        return hashtags_text

# ---------------- Load posts JSON ----------------
def load_posts_json(date=None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    path = f"output/metadata/posts_{date}.json"
    if not os.path.exists(path):
        log(f"No JSON file found for {date} at {path}")
        return []
    with open(path, "r") as f:
        return json.load(f)

# ---------------- Prepare tweets ----------------
def prepare_posts_for_tweeting(date=None):
    posts = load_posts_json(date)
    tweets = []
    for post in posts:
        text = build_tweet_text(post)
        images = post.get("images", [])
        if not images:
            log(f"Skipping post with no images: {text}")
            continue
        tweets.append({"text": text, "images": images})
    return tweets

# ---------------- Post to X (v2) ----------------
def post_tweets():
    # Read credentials from environment
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([bearer_token, api_key, api_secret, access_token, access_secret]):
        log("Twitter credentials are missing. Set them in environment variables.")
        return

    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )

    tweets = prepare_posts_for_tweeting()
    for tweet in tweets:
        media_ids = []
        for img in tweet["images"]:
            if os.path.exists(img):
                # v2 requires using media endpoint differently
                res = client.media_upload(filename=img)  # Adjust to correct v2 call if needed
                media_ids.append(res.media_id)
                log(f"Uploaded image: {img}")
            else:
                log(f"Image not found: {img}")
        if not media_ids:
            log(f"Skipping tweet (no images): {tweet['text']}")
            continue
        try:
            status = client.create_tweet(text=tweet["text"], media_ids=media_ids)
            log(f"Tweet posted successfully: {status.data['id']}")
        except Exception as e:
            log(f"Failed to post tweet: {tweet['text']}\nError: {e}")

# ---------------- Main ----------------
if __name__ == "__main__":
    post_tweets()
