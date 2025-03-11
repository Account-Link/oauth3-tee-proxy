# plugins/twitter/resource.py
"""
Twitter Resource Base Module
==========================

This module provides base functionality for Twitter resource plugins.
It serves as a starting point for implementing different Twitter resource
access methods and provides common utility functions.

This is meant to be used as a base for specific resource plugins like:
- Twitter API Resource (current web API)
- Twitter GraphQL Resource (future)
- Twitter OAuth2 Resource (future)

The base functionality includes common operations and utilities that are
shared across all Twitter resource access methods.
"""

import logging
from typing import Dict, Any, List, Optional

from plugins import ResourcePlugin

logger = logging.getLogger(__name__)

class TwitterBaseResourcePlugin(ResourcePlugin):
    """
    Base class for Twitter resource plugins.
    
    This abstract class provides common functionality for Twitter resource
    plugins, serving as a foundation for specific resource implementations.
    It defines the structure and common utilities for all Twitter resource
    plugins, ensuring consistency across different API access methods.
    
    Subclasses must implement the ResourcePlugin interface methods and
    can extend this base class with method-specific functionality.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin
                           (should be overridden by subclasses)
        SCOPES (Dict[str, str]): Dictionary mapping scope names to descriptions
    """
    
    service_name = "twitter_base"  # Should be overridden by subclasses
    
    SCOPES = {
        "tweet.post": "Permission to post tweets",
        "tweet.read": "Permission to read tweets",
        "tweet.delete": "Permission to delete tweets" 
    }
    
    async def initialize_client(self, credentials: Dict[str, Any]) -> Any:
        """
        Initialize a Twitter client with credentials.
        
        This method should be implemented by subclasses to create a client
        using the provided credentials that can be used for API calls.
        
        Args:
            credentials (Dict[str, Any]): The credentials to use
            
        Returns:
            Any: An initialized client object
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement initialize_client")
    
    async def validate_client(self, client: Any) -> bool:
        """
        Validate if the client is still valid.
        
        This method should be implemented by subclasses to check if the client's
        credentials are still valid and the client can make API calls.
        
        Args:
            client (Any): The client to validate
            
        Returns:
            bool: True if the client is valid, False otherwise
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement validate_client")
    
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