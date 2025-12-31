import os
import tweepy

# Read credentials from environment
api_key = os.getenv("TWITTER_API_KEY")
api_secret = os.getenv("TWITTER_API_KEY_SECRET")
access_token = os.getenv("TWITTER_ACCESS_TOKEN")
access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# OAuth1 Authentication
auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
api = tweepy.API(auth)

# Attempt a simple tweet
try:
    status = api.update_status("Test tweet from GitHub Actions – no images")
    print(f"Tweet posted successfully: {status.id}")
except tweepy.errors.Forbidden as e:
    print("Forbidden error:", e.response.text)
except Exception as e:
    print("Other error:", str(e))
