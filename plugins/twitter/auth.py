# plugins/twitter/auth.py
"""
Twitter Authorization Base Module
===============================

This module provides base functionality for Twitter authorization plugins.
It serves as a starting point for implementing different Twitter authorization
methods and provides common utility functions.

This is meant to be used as a base for specific authorization plugins like:
- Twitter Cookie Authorization
- Twitter OAuth2 Authorization (future)
- Twitter API Key Authorization (future)

The base functionality includes common operations and utilities that are
shared across all Twitter authorization methods.
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