import os
import json
from datetime import datetime
from logger import log
import tweepy
import traceback

# ---------------- Build tweet text ----------------
def build_tweet_text(post):
    hashtags = ["#SPXVisuals"]  # Always first

    # Add ticker if present
    if post.get("ticker"):
        hashtags.append(f"#{post['ticker']}")

    # Generic hashtags
    hashtags.extend([
        "#SPX", "#S&P500", "#SP500", "#SAndP500",
        "#Equities", "#Stocks", "#Market", "#StockMarket", "#Investing"
    ])

    # Chart type hashtags
    type_tag_map = {
        "ma": "#SMA #EMA",
        "normalized": "#PriceChart",
        "marketcap": "#MarketCap",
        "pe": "#PE"
    }
    hashtags.append(type_tag_map.get(post["type"], ""))

    hashtags_text = " ".join(hashtags)

    # Determine timeframe / ranges for text
    timeframe_text = ""
    range_text = ""

    if post["type"] == "ma" and post["images"]:
        fname = os.path.basename(post["images"][0])
        if "_" in fname:
            timeframe = fname.split("_")[-1].replace(".png", "")
            timeframe_text = timeframe

    elif post["type"] == "normalized" and post["images"]:
        fname = os.path.basename(post["images"][0])
        timeframe = fname.split("_")[0]
        timeframe_text = timeframe
        idx_part = fname.split("_")[1]
        idx_num = int(idx_part.split(".")[0])
        if idx_num == 0:
            range_text = "#1–#10"
        elif idx_num == 1:
            range_text = "#11–#20"
        elif idx_num == 2:
            range_text = "#21–#30"
        elif idx_num == 3:
            range_text = "#31–#40"
        elif idx_num == 4:
            range_text = "#41–#50"

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
        posts = json.load(f)
    return posts

# ---------------- Prepare tweets ----------------
def prepare_posts_for_tweeting(date=None):
    posts = load_posts_json(date)
    tweets = []
    for post in posts:
        text = build_tweet_text(post)
        images = post.get("images", [])
        # Skip posts with no images
        if not images:
            log(f"Skipping post with no images: {text}")
            continue
        tweets.append({
            "text": text,
            "images": images
        })
    return tweets

# ---------------- Post to X ----------------
def post_tweets():
    # Read credentials from environment
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        log("Twitter credentials are missing. Set them in environment variables.")
        return

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api = tweepy.API(auth)

    tweets = prepare_posts_for_tweeting()
    for tweet in tweets:
        try:
            media_ids = []
            for img in tweet["images"]:
                abs_path = os.path.abspath(img)
                log(f"Attempting to upload image: {img} -> {abs_path}")
                if os.path.exists(img):
                    res = api.media_upload(img)
                    media_ids.append(res.media_id_string)
                    log(f"Uploaded image: {img}")
                else:
                    log(f"Image file not found: {img}")
            if not media_ids:
                log(f"Skipping tweet (no valid images): {tweet['text']}")
                continue
            log(f"Posting tweet: {tweet['text']}")
            log(f"Media IDs to attach: {media_ids}")
            status = api.update_status(status=tweet["text"], media_ids=media_ids)
            log(f"Tweet posted successfully: {status.id}")
        except tweepy.errors.Forbidden as e:
            # Log full Forbidden response for debugging
            log(f"403 Forbidden when posting tweet: {tweet['text']}\nResponse text: {e.response.text}\nTraceback:\n{traceback.format_exc()}")
        except Exception as e:
            # Catch other exceptions
            log(f"Failed to post tweet: {tweet['text']}\nError: {e}\nTraceback:\n{traceback.format_exc()}")


# ---------------- Main ----------------
if __name__ == "__main__":
    post_tweets()








