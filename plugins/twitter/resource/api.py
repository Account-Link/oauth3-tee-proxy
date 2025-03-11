# plugins/twitter/resource/api.py
"""
Twitter API Resource Plugin
=========================

This module implements the Twitter API resource plugin for the OAuth3 TEE Proxy.
It handles interaction with the Twitter API on behalf of users, providing
functionality for posting tweets and other Twitter operations.

The TwitterApiResourcePlugin class implements the ResourcePlugin interface,
providing methods for:
- Initializing Twitter API clients with user credentials
- Validating Twitter API clients
- Defining available scopes for Twitter operations
- Posting tweets using the Twitter API

The plugin uses the TwitterApiClient wrapper class that encapsulates the
interaction with the Twitter API, providing a simplified interface for
common operations and handling errors in a consistent way.

Supported Scopes:
---------------
- tweet.post: Permission to post tweets
- tweet.read: Permission to read tweets
- tweet.delete: Permission to delete tweets
"""

import logging
import traceback
from typing import Dict, Any, List, Optional

from plugins.twitter.resource import TwitterBaseResourcePlugin
from twitter.account import Account

logger = logging.getLogger(__name__)

class TwitterApiClient:
    """
    Twitter API client wrapper used by the resource plugin.
    
    This class wraps the twitter.account.Account class, providing a simplified
    interface for interacting with the Twitter API. It handles errors and provides
    async-compatible methods for common Twitter operations.
    
    The TwitterApiClient is created by the TwitterApiResourcePlugin using the credentials
    stored in the database. It is responsible for making API calls to Twitter and
    handling the responses.
    
    Attributes:
        account (Account): The underlying Twitter Account object used for API calls
    """
    
    def __init__(self, account: Account):
        """
        Initialize with a Twitter Account object.
        
        Args:
            account (Account): The Twitter Account object to use for API calls
        """
        self.account = account
    
    async def validate(self) -> bool:
        """
        Validate if the client is still working.
        
        Makes a lightweight API call to Twitter to check if the client's credentials
        are still valid. Returns True if the call succeeds, False otherwise.
        
        Returns:
            bool: True if the client is valid, False otherwise
        """
        try:
            self.account.bookmarks(limit=1)
            return True
        except Exception as e:
            logger.error(f"Error validating Twitter API client: {e}")
            return False
            
    async def post_tweet(self, text: str) -> str:
        """
        Post a tweet and return the tweet ID.
        
        Posts a tweet with the given text using the Twitter API and returns
        the ID of the newly created tweet.
        
        Args:
            text (str): The text of the tweet to post
            
        Returns:
            str: The ID of the posted tweet
            
        Raises:
            ValueError: If the tweet ID cannot be extracted from the response
            Exception: If any other error occurs during the operation
        """
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

class TwitterApiResourcePlugin(TwitterBaseResourcePlugin):
    """
    Plugin for Twitter API resource operations.
    
    This class implements the ResourcePlugin interface for Twitter API operations,
    providing methods for initializing Twitter clients, validating clients,
    and performing operations like posting tweets.
    
    The plugin defines the available scopes for Twitter operations and provides
    methods for working with these scopes. It serves as a bridge between the
    OAuth3 TEE Proxy and the Twitter API.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin ("twitter")
    """
    
    service_name = "twitter"  # Keep the main service name for backward compatibility
    
    # We inherit SCOPES from the base class
    
    async def initialize_client(self, credentials: Dict[str, Any]) -> TwitterApiClient:
        """
        Initialize Twitter client with credentials.
        
        Creates a new TwitterApiClient instance using the provided credentials.
        This method is called by the TEE Proxy when it needs to make Twitter
        API calls on behalf of a user.
        
        Args:
            credentials (Dict[str, Any]): The Twitter credentials (e.g., cookie)
            
        Returns:
            TwitterApiClient: An initialized Twitter client
            
        Raises:
            Exception: If the client cannot be initialized
        """
        try:
            account = Account(cookies=credentials)
            return TwitterApiClient(account)
        except Exception as e:
            logger.error(f"Error initializing Twitter API client: {e}")
            raise
    
    async def validate_client(self, client: TwitterApiClient) -> bool:
        """
        Validate if the Twitter client is still valid.
        
        Checks if the Twitter client's credentials are still valid by making
        a lightweight API call to Twitter.
        
        Args:
            client (TwitterApiClient): The client to validate
            
        Returns:
            bool: True if the client is valid, False otherwise
        """
        return await client.validate()
    
    def get_available_scopes(self) -> List[str]:
        """
        Get the list of scopes supported by this resource plugin.
        
        Returns the list of scope names that can be requested for Twitter
        operations. These scopes define the permissions that clients can
        request when accessing Twitter resources.
        
        Returns:
            List[str]: List of scope strings
        """
        return list(self.SCOPES.keys())
    
    async def post_tweet(self, client: TwitterApiClient, text: str) -> str:
        """
        Post a tweet using the client.
        
        Posts a tweet with the given text using the provided TwitterApiClient.
        This method is called by the TEE Proxy when a client with the
        'tweet.post' scope requests to post a tweet.
        
        Args:
            client (TwitterApiClient): The Twitter client to use
            text (str): The text of the tweet to post
            
        Returns:
            str: The ID of the posted tweet
            
        Raises:
            Exception: If the tweet cannot be posted
        """
        return await client.post_tweet(text)
    
