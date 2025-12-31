import os
import tweepy

# Read credentials from environment
api_key = os.getenv("TWITTER_API_KEY")
api_secret = os.getenv("TWITTER_API_KEY_SECRET")
access_token = os.getenv("TWITTER_ACCESS_TOKEN")
access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

if not all([api_key, api_secret, access_token, access_secret]):
    print("Error: Missing Twitter credentials in environment variables")
    exit(1)

try:
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api = tweepy.API(auth)
    
    user = api.verify_credentials()
    if user:
        print(f"Authentication successful! Logged in as: @{user.screen_name}")
    else:
        print("Authentication failed: verify_credentials returned None")

except tweepy.TweepyException as e:
    print(f"Authentication failed: {e}")
