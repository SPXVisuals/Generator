import os
import json
from datetime import datetime
from logger import log
import tweepy
import time
import random

# ---------------- Build tweet text ----------------
def build_tweet_text(post):
    website_text = "\nSee more at https://spxvisuals.github.io"
    hashtags = ["#SPXVisuals"]  # Always first

    if post.get("ticker"):
        hashtags.append(f"#{post['ticker']}")

    hashtags.extend([
        "#SPX", "#SP500", "#SAndP500",
        "#Equities", "#Stocks", "#Market", "#StockMarket", "#Investing"
    ])

    type_tag_map = {
        "ma": "#SMA #EMA",
        "normalized": "#PriceChart",
        "marketcap": "#MarketCapitalization #MarketCap",
        "pe": "#PE",
        "gainers_losers": "#MarketLeaders #MarketLaggards"
    }
    hashtags.append(type_tag_map.get(post["type"], ""))
    hashtags_text = " ".join(hashtags)

    timeframe_text = ""

    if post["type"] == "ma" and post["images"]:
        fname = os.path.basename(post["images"][0])
        if "_" in fname:
            timeframe = fname.split("_")[-1].replace(".png", "")
            timeframe_text = timeframe
    elif post["type"] == "normalized" and post["images"]:
        fname = os.path.basename(post["images"][0])
        timeframe_text = fname.split("_")[1]

    # Build text per type
    if post["type"] == "ma":
        return f"{timeframe_text} - {post['ticker']} SMA & EMA Charts 📈 {hashtags_text}{website_text}"
    elif post["type"] == "normalized":
        return f"{timeframe_text} - Normalized Price Charts For The 40 Largest S&P 500 Index Components 📈 {hashtags_text}{website_text}"
    elif post["type"] == "marketcap":
        return f"Market Capitalization Distribution Charts For The 50 Largest S&P 500 Index Components 🍩 📊 {hashtags_text}{website_text}"
    elif post["type"] == "pe":
        pe_type = "Trailing" if "trailing" in post.get("images", [""])[0] else "Forward"
        return f"{pe_type} P/E Chart For The 50 Largest S&P 500 Index Components 📊 {hashtags_text}{website_text}"
    elif post["type"] == "gainers_losers":
        timeframe = post.get("timeframe", "")
        return (
            f"{timeframe} - S&P 500 Index Components' Performance Leaders vs Laggards 📋 {hashtags_text}{website_text}"
        )
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

    # v1.1 auth for media upload
    auth_v1 = tweepy.OAuth1UserHandler(
        api_key,
        api_secret,
        access_token,
        access_secret
    )
    api_v1 = tweepy.API(auth_v1)

    # v2 client for posting tweets
    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )

    time.sleep(random.randint(0, 30 * 60))
    tweets = prepare_posts_for_tweeting()
    for tweet in tweets:
        media_ids = []
        for img in tweet["images"]:
            if os.path.exists(img):
                res = api_v1.media_upload(filename=img)  # v1.1 upload
                media_ids.append(res.media_id_string)
                log(f"Uploaded image: {img}")
            else:
                log(f"Image not found: {img}")

        if not media_ids:
            log(f"Skipping tweet (no images): {tweet['text']}")
            continue

        try:
            status = client.create_tweet(text=tweet["text"], media_ids=media_ids)  # v2 post
            tweet_id = status.data["id"]
            log(f"Tweet posted successfully: {status.data['id']}")
            update_metadata_with_tweet(tweet, tweet_id)
            time.sleep(random.randint(25 * 60, 45 * 60))
        except Exception as e:
            log(f"Failed to post tweet: {tweet['text']}\nError: {e}")
            # Try to extract full HTTP info if available
            if hasattr(e, "response") and e.response is not None:
                resp = e.response
                headers = dict(resp.headers)
                status = getattr(resp, "status_code", None)
                body = getattr(resp, "text", None)

            # Log basic info
            log(f"HTTP status: {status}")
            log(f"Response body: {body}")
            log(f"All headers: {headers}")

            # Log rate-limit headers if present
            rate_headers = {k: v for k, v in headers.items() if "x-rate-limit" in k.lower()}
            log(f"Rate-limit headers: {rate_headers}")

            # Optional: human-readable reset time
            reset_ts = rate_headers.get("x-rate-limit-reset")
            if reset_ts:
                from datetime import datetime
                readable = datetime.fromtimestamp(int(reset_ts)).strftime("%Y-%m-%d %H:%M:%S")
                log(f"Rate limit resets at: {readable}")
        else:
            log("No HTTP response available in exception, cannot show headers or rate-limit info.")

def update_metadata_with_tweet(tweet, tweet_id):
    date = datetime.now().strftime("%Y-%m-%d")
    meta_path = f"output/metadata/posts_{date}.json"

    if not os.path.exists(meta_path):
        log(f"Metadata file not found: {meta_path}")
        return

    with open(meta_path, "r") as f:
        posts = json.load(f)

    updated = False
    for post in posts:
        post_images = post.get("images", [])
        if not post_images:
            continue

        # Match by first image filename
        if os.path.basename(post_images[0]) == os.path.basename(tweet["images"][0]):
            post["tweet_id"] = tweet_id
            post["tweet_text"] = tweet["text"]
            post["tweet_url"] = f"https://x.com/YOUR_HANDLE/status/{tweet_id}"
            updated = True
            break

    if updated:
        with open(meta_path, "w") as f:
            json.dump(posts, f, indent=2)
        log(f"Metadata updated with tweet ID {tweet_id}")
    else:
        log("WARNING: No matching metadata post found for tweet")

# ---------------- Main ----------------
if __name__ == "__main__":
    post_tweets()



