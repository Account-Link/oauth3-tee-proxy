"""
Plugin System for OAuth3 TEE Proxy
================================

This module defines the interfaces and base classes for plugins.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set, Tuple, Union, Type

# Global registries for different plugin types
_authorization_plugins: Dict[str, Type["AuthorizationPlugin"]] = {}
_resource_plugins: Dict[str, Type["ResourcePlugin"]] = {}
_route_plugins: Dict[str, Type["RoutePlugin"]] = {}

class AuthorizationPlugin(ABC):
    """
    Base interface for plugins that provide authorization functionality.
    
    An authorization plugin is responsible for authenticating users with a
    specific service and generating credentials that can be used to access
    that service's API.
    """
    
    @abstractmethod
    def get_plugin_id(self) -> str:
        """
        Get the unique identifier for this authorization plugin.
        
        Returns:
            str: The plugin ID (e.g., "twitter-oauth", "twitter-cookie")
        """
        pass
    
    @abstractmethod
    def get_display_name(self) -> str:
        """
        Get a human-readable name for this authorization method.
        
        Returns:
            str: The display name (e.g., "Twitter OAuth", "Twitter Cookie Auth")
        """
        pass
    
    def get_auth_scopes(self) -> List[str]:
        """
        Get the auth scopes this plugin requires.
        
        Returns:
            List[str]: List of required scopes
        """
        return []

class ResourcePlugin(ABC):
    """
    Base interface for plugins that provide access to external resources.
    
    A resource plugin is responsible for providing access to external resources
    such as APIs, databases, or other services. It typically uses credentials
    obtained from an authorization plugin to authenticate requests to the
    external service.
    """
    
    @abstractmethod
    def get_plugin_id(self) -> str:
        """
        Get the unique identifier for this resource plugin.
        
        Returns:
            str: The plugin ID (e.g., "twitter", "telegram")
        """
        pass
    
    def get_available_scopes(self) -> List[str]:
        """
        Get the available scopes for this resource.
        
        Returns:
            List[str]: List of available scopes
        """
        return []
    
    @property
    def SCOPES(self) -> Dict[str, str]:
        """
        Get the scope descriptions for this resource.
        
        Returns:
            Dict[str, str]: Dictionary mapping scope names to descriptions
        """
        return {}

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

# Plugin registration functions
def register_authorization_plugin(service_name: str, plugin_class: Type[AuthorizationPlugin]) -> None:
    """
    Register an authorization plugin for a service.
    
    Args:
        service_name (str): The unique name of the service this plugin authenticates with
        plugin_class (Type[AuthorizationPlugin]): The plugin class to register
    """
    _authorization_plugins[service_name] = plugin_class

def register_resource_plugin(service_name: str, plugin_class: Type[ResourcePlugin]) -> None:
    """
    Register a resource plugin for a service.
    
    Args:
        service_name (str): The unique name of the service this plugin provides access to
        plugin_class (Type[ResourcePlugin]): The plugin class to register
    """
    _resource_plugins[service_name] = plugin_class

def register_route_plugin(service_name: str, plugin_class: Type[RoutePlugin]) -> None:
    """
    Register a route plugin for a service.
    
    Args:
        service_name (str): The unique name of the service this plugin provides routes for
        plugin_class (Type[RoutePlugin]): The plugin class to register
    """
    _route_plugins[service_name] = plugin_class

# Plugin retrieval functions
def get_authorization_plugin(service_name: str) -> Optional[Type[AuthorizationPlugin]]:
    """
    Get an authorization plugin by service name.
    
    Args:
        service_name (str): The unique name of the service
        
    Returns:
        Optional[Type[AuthorizationPlugin]]: The plugin class if registered, None otherwise
    """
    return _authorization_plugins.get(service_name)

def get_resource_plugin(service_name: str) -> Optional[Type[ResourcePlugin]]:
    """
    Get a resource plugin by service name.
    
    Args:
        service_name (str): The unique name of the service
        
    Returns:
        Optional[Type[ResourcePlugin]]: The plugin class if registered, None otherwise
    """
    return _resource_plugins.get(service_name)

def get_route_plugin(service_name: str) -> Optional[Type[RoutePlugin]]:
    """
    Get a route plugin by service name.
    
    Args:
        service_name (str): The unique name of the service
        
    Returns:
        Optional[Type[RoutePlugin]]: The plugin class if registered, None otherwise
    """
    return _route_plugins.get(service_name)

# Collection functions
def get_all_authorization_plugins() -> Dict[str, Type[AuthorizationPlugin]]:
    """
    Get all registered authorization plugins.
    
    Returns:
        Dict[str, Type[AuthorizationPlugin]]: Dictionary mapping service names to plugin classes
    """
    return _authorization_plugins.copy()

def get_all_resource_plugins() -> Dict[str, Type[ResourcePlugin]]:
    """
    Get all registered resource plugins.
    
    Returns:
        Dict[str, Type[ResourcePlugin]]: Dictionary mapping service names to plugin classes
    """
    return _resource_plugins.copy()

def get_all_route_plugin_classes() -> Dict[str, Type[RoutePlugin]]:
    """
    Get all registered route plugins.
    
    Returns:
        Dict[str, Type[RoutePlugin]]: Dictionary mapping service names to plugin classes
    """
    return _route_plugins.copy()