# plugins/twitter/auth/__init__.py
"""
Twitter Authorization Plugins
============================

This package contains authorization plugins for Twitter, providing authentication
mechanisms for Twitter integration in the OAuth3 TEE Proxy.

The package includes different authorization mechanisms:
- Cookie-based authentication: Handles Twitter authentication using browser cookies
- OAuth-based authentication: Handles Twitter authentication using OAuth 1.0a

Each authorization plugin implements the AuthorizationPlugin interface defined in
the plugins module, providing a consistent way to authenticate with Twitter.
"""

import logging
from typing import Dict, Any, Optional

from plugins import AuthorizationPlugin

logger = logging.getLogger(__name__)

class TwitterBaseAuthorizationPlugin(AuthorizationPlugin):
    """
    Base class for Twitter authorization plugins.
    
    This abstract class provides common functionality for Twitter authorization
    plugins, serving as a foundation for specific authorization implementations.
    It defines the structure and common utilities for all Twitter authorization
    plugins, ensuring consistency across different authentication methods.
    
    Subclasses must implement the AuthorizationPlugin interface methods and
    can extend this base class with method-specific functionality.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin
                           (should be overridden by subclasses)
    """
    
    service_name = "twitter_base"  # Should be overridden by subclasses
    
    def get_plugin_id(self) -> str:
        """
        Get the unique identifier for this authorization plugin.
        
        This method should be overridden by subclasses to return the plugin ID.
        
        Returns:
            str: The plugin ID
        """
        raise NotImplementedError("Subclasses must implement get_plugin_id")
    
    def get_display_name(self) -> str:
        """
        Get a human-readable name for this authorization method.
        
        This method should be overridden by subclasses to return the display name.
        
        Returns:
            str: The display name
        """
        raise NotImplementedError("Subclasses must implement get_display_name")
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate if the credentials are valid.
        
        This method should be implemented by subclasses to validate credentials
        against the Twitter API or service.
        
        Args:
            credentials (Dict[str, Any]): The credentials to validate
            
        Returns:
            bool: True if the credentials are valid, False otherwise
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement validate_credentials")
    
    async def get_user_identifier(self, credentials: Dict[str, Any]) -> str:
        """
        Get Twitter user ID from the credentials.
        
        This method should be implemented by subclasses to extract a user
        identifier from the credentials.
        
        Args:
            credentials (Dict[str, Any]): The credentials to extract the identifier from
            
        Returns:
            str: The Twitter user ID
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement get_user_identifier")
    
    def credentials_to_string(self, credentials: Dict[str, Any]) -> str:
        """
        Convert credentials dictionary to a string representation.
        
        This method should be implemented by subclasses to serialize credentials
        for storage in the database.
        
        Args:
            credentials (Dict[str, Any]): The credentials to convert
            
        Returns:
            str: String representation of the credentials
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement credentials_to_string")
    
    def credentials_from_string(self, credentials_str: str) -> Dict[str, Any]:
        """
        Convert a string representation back to credentials dictionary.
        
        This method should be implemented by subclasses to deserialize credentials
        from the database.
        
        Args:
            credentials_str (str): String representation of credentials
            
        Returns:
            Dict[str, Any]: The deserialized credentials
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement credentials_from_string")

# Import plugins AFTER defining base class
from .cookie import TwitterCookieAuthorizationPlugin
from .oauth import TwitterOAuthAuthorizationPlugin