# plugins/twitter/auth/oauth.py
"""
Twitter OAuth Authentication Plugin
==================================

This module implements a Twitter OAuth1.0a authentication plugin for the OAuth3 TEE Proxy.
It handles the Twitter OAuth flow for authentication, token handling, and session management.

The TwitterOAuthAuthorizationPlugin class implements the AuthorizationPlugin interface,
providing methods for:
- Initiating Twitter OAuth flow
- Processing OAuth callbacks
- Managing OAuth tokens and credentials
- Validating OAuth token credentials
- Retrieving user information

This plugin uses the tweepy library to interact with Twitter's OAuth API.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import tweepy
import json
import uuid
from datetime import datetime

from plugins import AuthorizationPlugin
from plugins.twitter.config import get_twitter_settings

# Set up logging
logger = logging.getLogger(__name__)

# Get Twitter settings
settings = get_twitter_settings()

class TwitterOAuthAuthorizationPlugin(AuthorizationPlugin):
    """
    Plugin for Twitter OAuth authorization.
    
    This class implements the AuthorizationPlugin interface for Twitter OAuth,
    providing methods for initiating Twitter OAuth flow, processing callbacks,
    validating credentials, and retrieving user information.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin
    """
    
    service_name = "twitter_oauth"
    
    def __init__(self):
        """Initialize the Twitter OAuth authorization plugin."""
        # Validation checks for required settings
        if not settings.TWITTER_CONSUMER_KEY or not settings.TWITTER_CONSUMER_SECRET:
            logger.warning("Twitter OAuth plugin initialized without API keys")
    
    def get_oauth_handler(self, callback_url: Optional[str] = None) -> tweepy.OAuth1UserHandler:
        """
        Get a Twitter OAuth handler instance.
        
        Args:
            callback_url (Optional[str]): Custom callback URL for the OAuth flow
            
        Returns:
            tweepy.OAuth1UserHandler: Configured OAuth handler
        """
        return tweepy.OAuth1UserHandler(
            settings.TWITTER_CONSUMER_KEY,
            settings.TWITTER_CONSUMER_SECRET,
            callback=callback_url or settings.TWITTER_OAUTH_CALLBACK_URL
        )
    
    async def get_authorization_url(self, callback_url: Optional[str] = None) -> Tuple[str, Any]:
        """
        Generate a Twitter authorization URL.
        
        This method creates an OAuth flow URL that directs the user to Twitter's
        authentication page, where they can authorize the application.
        
        Args:
            callback_url (Optional[str]): Custom callback URL for the OAuth flow
            
        Returns:
            Tuple[str, Any]: The authorization URL and request token
        """
        auth = self.get_oauth_handler(callback_url)
        redirect_url = auth.get_authorization_url(signin_with_twitter=True)
        request_token = auth.request_token
        
        # Return both for storage/validation
        return redirect_url, request_token
    
    async def process_callback(self, request_token: Dict[str, str], oauth_verifier: str) -> Dict[str, Any]:
        """
        Process OAuth callback and get access token.
        
        This method exchanges the request token and verifier for an access token
        after the user has authorized the application on Twitter.
        
        Args:
            request_token (Dict[str, str]): The request token from the initial OAuth request
            oauth_verifier (str): The OAuth verifier returned by Twitter
            
        Returns:
            Dict[str, Any]: OAuth credentials including tokens and user information
            
        Raises:
            ValueError: If the OAuth flow fails
        """
        auth = self.get_oauth_handler()
        auth.request_token = request_token
        
        try:
            # Get access token
            access_token, access_token_secret = auth.get_access_token(oauth_verifier)
            
            # Get user information
            user_info = await self.get_user_info(access_token, access_token_secret)
            
            # Combine everything into credentials
            credentials = {
                "oauth_token": access_token,
                "oauth_token_secret": access_token_secret,
                "user_id": user_info["id"],
                "screen_name": user_info["screen_name"],
                "name": user_info.get("name", ""),
                "profile_image_url": user_info.get("profile_image_url", "")
            }
            
            return credentials
        except tweepy.TweepyException as e:
            logger.error(f"Twitter OAuth error: {str(e)}")
            raise ValueError(f"Failed to complete Twitter OAuth: {str(e)}")
    
    async def get_user_info(self, access_token: str, access_token_secret: str) -> Dict[str, Any]:
        """
        Get Twitter user information using access tokens.
        
        Args:
            access_token (str): The Twitter OAuth access token
            access_token_secret (str): The Twitter OAuth access token secret
            
        Returns:
            Dict[str, Any]: User information from Twitter
            
        Raises:
            ValueError: If user information cannot be retrieved
        """
        auth = self.get_oauth_handler()
        auth.set_access_token(access_token, access_token_secret)
        
        try:
            api = tweepy.API(auth)
            user = api.verify_credentials()
            
            return {
                "id": user.id_str,
                "screen_name": user.screen_name,
                "name": user.name,
                "profile_image_url": user.profile_image_url_https
            }
        except tweepy.TweepyException as e:
            logger.error(f"Error getting Twitter user info: {str(e)}")
            raise ValueError(f"Failed to get Twitter user info: {str(e)}")
    
    def credentials_to_string(self, credentials: Dict[str, Any]) -> str:
        """
        Convert credentials to a storage-friendly string.
        
        Args:
            credentials (Dict[str, Any]): The OAuth credentials
            
        Returns:
            str: JSON string representation of the credentials
        """
        return json.dumps(credentials)
    
    def credentials_from_string(self, credentials_str: str) -> Dict[str, Any]:
        """
        Convert a storage-friendly string back to credentials.
        
        Args:
            credentials_str (str): JSON string representation of the credentials
            
        Returns:
            Dict[str, Any]: The OAuth credentials
            
        Raises:
            ValueError: If the credentials string is invalid
        """
        try:
            return json.loads(credentials_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Twitter OAuth credentials: {str(e)}")
            raise ValueError("Invalid Twitter OAuth credentials format")
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate if the stored credentials are still valid.
        
        Args:
            credentials (Dict[str, Any]): The OAuth credentials to validate
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            # Extract OAuth tokens from credentials
            oauth_token = credentials.get("oauth_token")
            oauth_token_secret = credentials.get("oauth_token_secret")
            
            if not oauth_token or not oauth_token_secret:
                return False
            
            # Try to get user info with these tokens
            await self.get_user_info(oauth_token, oauth_token_secret)
            return True
        except Exception as e:
            logger.error(f"Twitter OAuth credentials validation failed: {str(e)}")
            return False
    
    async def get_user_identifier(self, credentials: Dict[str, Any]) -> str:
        """
        Get a unique identifier for the user from the credentials.
        
        Args:
            credentials (Dict[str, Any]): The OAuth credentials
            
        Returns:
            str: Unique identifier for the user (Twitter ID)
            
        Raises:
            ValueError: If user identifier cannot be extracted
        """
        # First try to get it from the cached credentials
        user_id = credentials.get("user_id")
        if user_id:
            return user_id
        
        # If not available, try to fetch from Twitter API
        oauth_token = credentials.get("oauth_token")
        oauth_token_secret = credentials.get("oauth_token_secret")
        
        if not oauth_token or not oauth_token_secret:
            raise ValueError("OAuth tokens not found in credentials")
        
        try:
            user_info = await self.get_user_info(oauth_token, oauth_token_secret)
            return user_info["id"]
        except Exception as e:
            logger.error(f"Error getting Twitter user identifier: {str(e)}")
            raise ValueError(f"Failed to get Twitter user identifier: {str(e)}")
    
    async def refresh_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refresh credentials if needed.
        
        Twitter OAuth 1.0a tokens don't expire, so this method just validates them
        and returns the original credentials.
        
        Args:
            credentials (Dict[str, Any]): The OAuth credentials
            
        Returns:
            Dict[str, Any]: The same credentials if valid
            
        Raises:
            ValueError: If credentials are invalid
        """
        # OAuth 1.0a tokens don't expire, so just validate them
        if await self.validate_credentials(credentials):
            return credentials
        else:
            raise ValueError("Invalid Twitter OAuth credentials")