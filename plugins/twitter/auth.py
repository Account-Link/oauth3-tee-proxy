# plugins/twitter/auth.py
"""
Twitter authorization plugin for OAuth3 TEE Proxy.
"""

import json
import logging
from typing import Dict, Any, Optional

from plugins import AuthorizationPlugin
from twitter.account import Account

logger = logging.getLogger(__name__)

class TwitterAuthorizationPlugin(AuthorizationPlugin):
    """Plugin for Twitter authentication using cookies."""
    
    service_name = "twitter"
    
    @classmethod
    def create_from_cookie_string(cls, cookie_string: str) -> "TwitterAuthorizationPlugin":
        """Create plugin instance from a cookie string."""
        plugin = cls()
        plugin.credentials = plugin.credentials_from_string(cookie_string)
        return plugin
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validate if the Twitter cookie is still valid."""
        try:
            account = Account(cookies=credentials)
            # Try a lightweight API call to check if the cookie is valid
            account.bookmarks(limit=1)
            return True
        except Exception as e:
            logger.error(f"Error validating Twitter credentials: {e}")
            return False
    
    async def get_user_identifier(self, credentials: Dict[str, Any]) -> str:
        """Get Twitter user ID from the credentials."""
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
        """Convert credentials dictionary to a JSON string."""
        return json.dumps(credentials)
    
    def credentials_from_string(self, credentials_str: str) -> Dict[str, Any]:
        """Convert JSON string to credentials dictionary."""
        try:
            return json.loads(credentials_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Twitter credentials: {e}")
            raise ValueError("Invalid Twitter credentials format") from e