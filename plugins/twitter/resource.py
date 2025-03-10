# plugins/twitter/resource.py
"""
Twitter resource plugin for OAuth3 TEE Proxy.
"""

import logging
import traceback
from typing import Dict, Any, List, Optional

from plugins import ResourcePlugin
from twitter.account import Account

logger = logging.getLogger(__name__)

class TwitterClient:
    """Twitter client wrapper used by the resource plugin."""
    
    def __init__(self, account: Account):
        """Initialize with a Twitter Account object."""
        self.account = account
    
    async def validate(self) -> bool:
        """Validate if the client is still working."""
        try:
            self.account.bookmarks(limit=1)
            return True
        except Exception as e:
            logger.error(f"Error validating Twitter client: {e}")
            return False
            
    async def post_tweet(self, text: str) -> str:
        """Post a tweet and return the tweet ID."""
        try:
            response = self.account.tweet(text)
            logger.debug(f"Tweet response: {response}")
            
            tweet_data = response.get('data', {})
            tweet_id = str(tweet_data.get('id_str') or tweet_data.get('id'))
            
            if not tweet_id:
                raise ValueError("Could not extract tweet ID from response")
                
            return tweet_id
        except Exception as e:
            logger.error(f"Error posting tweet: {e}\nTraceback:\n{traceback.format_exc()}")
            raise

class TwitterResourcePlugin(ResourcePlugin):
    """Plugin for Twitter resource operations."""
    
    service_name = "twitter"
    
    SCOPES = {
        "tweet.post": "Permission to post tweets",
        "tweet.read": "Permission to read tweets",
        "tweet.delete": "Permission to delete tweets" 
    }
    
    async def initialize_client(self, credentials: Dict[str, Any]) -> TwitterClient:
        """Initialize Twitter client with credentials."""
        try:
            account = Account(cookies=credentials)
            return TwitterClient(account)
        except Exception as e:
            logger.error(f"Error initializing Twitter client: {e}")
            raise
    
    async def validate_client(self, client: TwitterClient) -> bool:
        """Validate if the Twitter client is still valid."""
        return await client.validate()
    
    def get_available_scopes(self) -> List[str]:
        """Get the list of scopes supported by this resource plugin."""
        return list(self.SCOPES.keys())
    
    async def post_tweet(self, client: TwitterClient, text: str) -> str:
        """Post a tweet using the client."""
        return await client.post_tweet(text)