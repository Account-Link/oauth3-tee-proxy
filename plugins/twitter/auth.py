# plugins/twitter/auth.py
"""
Twitter Authorization Plugin for OAuth3 TEE Proxy
================================================

This module implements the Twitter authorization plugin for the OAuth3 TEE Proxy.
It handles authentication with Twitter using cookie-based authentication, allowing
users to link their Twitter accounts to the TEE Proxy.

The TwitterAuthorizationPlugin class implements the AuthorizationPlugin interface,
providing methods for:
- Validating Twitter cookies
- Extracting Twitter user IDs from cookies
- Converting Twitter cookies between string and dictionary formats

This plugin works with the unofficial Twitter API client that uses browser cookies
for authentication, allowing the TEE Proxy to act on behalf of users without
requiring them to create Twitter developer accounts or using the official API.

Authentication Flow:
------------------
1. User submits their Twitter cookie string to the TEE Proxy
2. The plugin validates the cookie by making a test API call
3. The plugin extracts the Twitter user ID from the cookie
4. The cookie is stored in the database, linked to the user's account
5. The TEE Proxy can now make Twitter API calls on behalf of the user
"""

import json
import logging
from typing import Dict, Any, Optional

from plugins import AuthorizationPlugin
from twitter.account import Account

logger = logging.getLogger(__name__)

class TwitterAuthorizationPlugin(AuthorizationPlugin):
    """
    Plugin for Twitter authentication using cookies.
    
    This class implements the AuthorizationPlugin interface for Twitter authentication
    using browser cookies. It provides functionality for validating Twitter cookies,
    extracting Twitter user IDs, and converting cookies between string and dictionary
    formats.
    
    The plugin uses the unofficial Twitter API client (twitter.account.Account) that
    works with browser cookies for authentication. This approach allows the TEE Proxy
    to act on behalf of Twitter users without requiring developer API keys.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin ("twitter")
    """
    
    service_name = "twitter"
    
    @classmethod
    def create_from_cookie_string(cls, cookie_string: str) -> "TwitterAuthorizationPlugin":
        """
        Create a plugin instance from a raw cookie string.
        
        This factory method creates a new TwitterAuthorizationPlugin instance and
        initializes it with credentials parsed from the provided cookie string.
        
        Args:
            cookie_string (str): The raw Twitter cookie string in JSON format
            
        Returns:
            TwitterAuthorizationPlugin: An initialized plugin instance
            
        Raises:
            ValueError: If the cookie string cannot be parsed as JSON
        """
        plugin = cls()
        plugin.credentials = plugin.credentials_from_string(cookie_string)
        return plugin
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate if the Twitter cookie is still valid.
        
        Attempts to make a lightweight API call to Twitter using the provided
        credentials to check if they are still valid. The method fetches the
        user's bookmarks with a limit of 1 as a simple validation test.
        
        Args:
            credentials (Dict[str, Any]): The Twitter cookie credentials
            
        Returns:
            bool: True if the credentials are valid, False otherwise
            
        Note:
            This method catches all exceptions and returns False for any error,
            logging the error for debugging purposes.
        """
        try:
            account = Account(cookies=credentials)
            # Try a lightweight API call to check if the cookie is valid
            account.bookmarks(limit=1)
            return True
        except Exception as e:
            logger.error(f"Error validating Twitter credentials: {e}")
            return False
    
    async def get_user_identifier(self, credentials: Dict[str, Any]) -> str:
        """
        Get Twitter user ID from the credentials.
        
        Extracts the Twitter user ID from the credentials by initializing a
        Twitter Account object and requesting the user ID from it.
        
        Args:
            credentials (Dict[str, Any]): The Twitter cookie credentials
            
        Returns:
            str: The Twitter user ID
            
        Raises:
            ValueError: If the user ID cannot be extracted from the response
            Exception: If any other error occurs during the operation
        """
        try:
            account = Account(cookies=credentials)
            user_id = account.get_user_id()
            if not user_id:
                raise ValueError("Could not extract user ID from Twitter response")
            return user_id
        except Exception as e:
            logger.error(f"Error getting Twitter user ID: {e}")
            raise
    
    def credentials_to_string(self, credentials: Dict[str, Any]) -> str:
        """
        Convert credentials dictionary to a JSON string.
        
        Serializes the Twitter cookie credentials dictionary to a JSON string
        for storage in the database.
        
        Args:
            credentials (Dict[str, Any]): The Twitter cookie credentials
            
        Returns:
            str: The JSON string representation of the credentials
        """
        return json.dumps(credentials)
    
    def credentials_from_string(self, credentials_str: str) -> Dict[str, Any]:
        """
        Convert JSON string to credentials dictionary.
        
        Deserializes a JSON string representation of Twitter cookie credentials
        back into a dictionary that can be used by the plugin.
        
        Args:
            credentials_str (str): The JSON string representation of the credentials
            
        Returns:
            Dict[str, Any]: The deserialized Twitter cookie credentials
            
        Raises:
            ValueError: If the string cannot be parsed as JSON
        """
        try:
            return json.loads(credentials_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Twitter credentials: {e}")
            raise ValueError("Invalid Twitter credentials format") from e