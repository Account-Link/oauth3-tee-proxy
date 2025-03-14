"""
Plugin System for OAuth3 TEE Proxy
================================

This module defines the interfaces and base classes for plugins.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set

class RoutePlugin(ABC):
    """
    Base interface for plugins that provide routes.
    
    A route plugin can register FastAPI routers to expose API endpoints.
    """
    
    @abstractmethod
    def get_routers(self) -> Dict[str, Any]:
        """
        Get FastAPI routers provided by this plugin.
        
        Returns:
            Dict[str, Any]: Dictionary mapping service names to FastAPI routers
        """
        pass
    
    def get_scopes(self) -> Dict[str, str]:
        """
        Get OAuth2 scopes provided by this plugin.
        
        Returns:
            Dict[str, str]: Dictionary mapping scope names to descriptions
        """
        return {}
    
    def get_auth_requirements(self) -> Dict[str, List[str]]:
        """
        Get authentication requirements for routes.
        
        This method should return a dictionary mapping route patterns to
        a list of authentication types (e.g., "session", "oauth2", "none").
        The auth middleware will use these requirements to determine how to
        authenticate requests to the routes.
        
        Route patterns can include wildcards, e.g., "/twitter/api/*"
        
        Returns:
            Dict[str, List[str]]: Dictionary mapping route patterns to auth types
        """
        return {}
    
    def get_jwt_policy_scopes(self) -> Dict[str, Set[str]]:
        """
        Get JWT policy to scopes mapping for this plugin.
        
        This method should return a dictionary mapping JWT policy names to
        sets of scopes that are granted by that policy. For example, a plugin
        might define a "twitter-read-only" policy that grants read-only scopes.
        
        Returns:
            Dict[str, Set[str]]: Dictionary mapping policy names to scopes
        """
        return {}