# plugins/twitter/config.py
"""
Configuration for Twitter plugin
"""

from pydantic_settings import BaseSettings
from functools import lru_cache

class TwitterSettings(BaseSettings):
    """
    Twitter-specific settings
    
    These settings can be configured via environment variables
    prefixed with TWITTER_, e.g., TWITTER_MAX_TWEET_LENGTH
    """
    # Tweet settings
    MAX_TWEET_LENGTH: int = 280
    
    # Safety settings
    SAFETY_FILTER_ENABLED: bool = True
    
    # Scopes
    ALLOWED_SCOPES: str = "tweet.post tweet.read tweet.delete twitter.graphql twitter.graphql.read twitter.graphql.write twitter_oauth1.auth twitter_oauth1.tweet"
    
    # OAuth settings
    TWITTER_CONSUMER_KEY: str = ""
    TWITTER_CONSUMER_SECRET: str = ""
    TWITTER_OAUTH_CALLBACK_URL: str = "http://localhost:8000/twitter/oauth/callback"
    
    class Config:
        env_prefix = "TWITTER_"
        env_file = ".env"

@lru_cache()
def get_twitter_settings():
    """
    Get the Twitter settings, cached to avoid reloading
    """
    return TwitterSettings()