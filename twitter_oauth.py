from tweepy import OAuth1UserHandler
import tweepy
from config import get_settings

# Get settings
settings = get_settings()

def get_oauth_handler(callback_url=None):
    """Get a Twitter OAuth handler instance."""
    return OAuth1UserHandler(
        settings.TWITTER_CONSUMER_KEY,
        settings.TWITTER_CONSUMER_SECRET,
        callback=callback_url or settings.TWITTER_OAUTH_CALLBACK_URL
    )

def get_authorization_url(callback_url=None, csrf_token=None):
    """Generate a Twitter authorization URL."""
    auth = get_oauth_handler(callback_url)
    redirect_url = auth.get_authorization_url(signin_with_twitter=True)
    request_token = auth.request_token
    
    # Return both for storage/validation
    return redirect_url, request_token

def get_access_token(request_token, oauth_verifier):
    """Exchange request token for access token."""
    auth = get_oauth_handler()
    auth.request_token = request_token
    
    try:
        access_token, access_token_secret = auth.get_access_token(oauth_verifier)
        return access_token, access_token_secret
    except tweepy.TweepyException as e:
        raise ValueError(f"Failed to get access token: {str(e)}")

def get_twitter_user_info(access_token, access_token_secret):
    """Get Twitter user info using the provided tokens."""
    auth = get_oauth_handler()
    auth.set_access_token(access_token, access_token_secret)
    
    api = tweepy.API(auth)
    user = api.verify_credentials()
    
    return {
        "id": user.id_str,
        "screen_name": user.screen_name,
        "name": user.name,
        "profile_image_url": user.profile_image_url_https
    }

def post_tweet(access_token, access_token_secret, text):
    """Post a tweet using OAuth credentials with Twitter API v2."""
    client = tweepy.Client(
        consumer_key=settings.TWITTER_CONSUMER_KEY,
        consumer_secret=settings.TWITTER_CONSUMER_SECRET,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    
    try:
        response = client.create_tweet(text=text)
        return response.data['id']
    except tweepy.TweepyException as e:
        raise ValueError(f"Failed to post tweet: {str(e)}") 