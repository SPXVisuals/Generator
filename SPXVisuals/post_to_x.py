import os
import json
from datetime import datetime
from logger import log
import tweepy
import time
import random
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Determine mode: AM or PM
mode = sys.argv[1].upper() if len(sys.argv) > 1 else "PM"
RUN_DATE = datetime.now().strftime("%Y-%m-%d")

# ---------------- Build tweet text ----------------
def build_tweet_text(post):
    hashtags = ["#SPXVisuals"]  # Always first

    if post.get("ticker"):
        hashtags.append(f"${post['ticker']}")
        hashtags.append(f"#{post['ticker']}")
    else:
        hashtags.append(f"$SPY")
        
    hashtags.extend([
        "#SPY", "#SPX", "#SP500", "#SAndP500",
        "#Equities", "#Stocks", "#Market", "#StockMarket", "#Investing"
    ])

    type_tag_map = {
        "ma": "#SMA #EMA",
        "normalized": "#PriceChart",
        "marketcap": "#MarketCapitalization #MarketCap",
        "volume": "#Volume #TradingVolume",
        "pe": "#PE #PERatio #PriceToEarnings",
        "gainers_losers": "#MarketLeaders #MarketLaggards"
    }
    hashtags.append(type_tag_map.get(post["type"], ""))
    hashtags.append("🌐 spxvisuals.github.io")
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
        return f"{timeframe_text} - {post['ticker']} SMA & EMA Charts 📈 {hashtags_text}"
    elif post["type"] == "normalized":
        return f"{timeframe_text} - Normalized Price Charts For The 40 Largest S&P 500 Index Components 📈 {hashtags_text}"
    elif post["type"] == "marketcap":
        return f"Market Capitalization Distribution Charts For The 50 Largest S&P 500 Index Components 🍩 📊 {hashtags_text}"
    elif post["type"] == "volume":
        return f"Volume Distribution Charts For The 50 Largest S&P 500 Index Components 📊 {hashtags_text}"
    elif post["type"] == "pe":
        return f"Trailing And Forward P/E Ratio Charts For The 50 Largest S&P 500 Index Components 📊 {hashtags_text}"
    elif post["type"] == "gainers_losers":
        timeframe = post.get("timeframe", "")
        return (
            f"{timeframe} - S&P 500 Index Components' Performance Leaders vs Laggards 📋 {hashtags_text}"
        )
    else:
        return hashtags_text

# ---------------- Load posts JSON ----------------
def load_posts_json(date=None, mode=mode):
    if date is None:
        date = RUN_DATE
    path = f"output/metadata/posts_{date}_{mode.lower()}.json"
    if not os.path.exists(path):
        log(f"No JSON file found for {date} {mode} at {path}")
        return []
    with open(path, "r") as f:
        return json.load(f)

# ---------------- Prepare tweets ----------------
def prepare_posts_for_tweeting(date=None):
    posts = load_posts_json(date, mode=mode)
    tweets = []
    for post in posts:
        text = build_tweet_text(post)
        images = post.get("images", [])
        if not images:
            log(f"Skipping post with no images: {text}")
            continue
        tweets.append({"text": text, "images": images})
    return tweets

# ---------------- Retry Post ----------------
def post_with_retry(client, text, media_ids, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.create_tweet(text=text, media_ids=media_ids)
        except Exception as e:
            wait_time = (2 ** attempt) * 15  # 15s, 30s, 60s
            log(f"Post attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:
                log(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise e
                
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

    # Attach retry strategy to underlying session
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    client.session.mount("https://", adapter)

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
            status = post_with_retry(client, tweet["text"], media_ids)
            tweet_id = status.data["id"]
            log(f"Tweet posted successfully: {tweet_id}")
            update_metadata_with_tweet(tweet, tweet_id)
            time.sleep(random.randint(25 * 60, 45 * 60))
            
        except Exception as e:
            log(f"Failed to post tweet: {tweet['text']}\nError: {e}")

            status = None
            body = None
            headers = {}

            if hasattr(e, "response") and e.response is not None:
                resp = e.response
                headers = dict(resp.headers)
                status = getattr(resp, "status_code", None)
                body = getattr(resp, "text", None)

            log(f"HTTP status: {status}")
            log(f"Response body: {body}")
            log(f"All headers: {headers}")

            rate_headers = {k: v for k, v in headers.items() if "x-rate-limit" in k.lower()}
            log(f"Rate-limit headers: {rate_headers}")

            reset_ts = rate_headers.get("x-rate-limit-reset")
            if reset_ts:
                readable = datetime.fromtimestamp(int(reset_ts)).strftime("%Y-%m-%d %H:%M:%S")
                log(f"Rate limit resets at: {readable}")

def update_metadata_with_tweet(tweet, tweet_id):
    date = RUN_DATE
    meta_path = f"output/metadata/posts_{date}_{mode.lower()}.json"

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














