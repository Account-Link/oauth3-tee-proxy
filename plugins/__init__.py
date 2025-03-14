# plugins/__init__.py
"""
Plugin System for OAuth3 TEE Proxy
==================================

This module provides the foundation for the plugin architecture of the OAuth3 TEE Proxy.
It defines the base interfaces that all plugins must implement and provides
functionality for plugin registration and management.

The plugin system supports two primary types of plugins:
1. Authorization Plugins: Handle authentication with resource servers
2. Resource Plugins: Interact with resource server APIs

Design Philosophy:
-----------------
The plugin architecture follows these principles:
- Clear separation of concerns between authorization and resource access
- Consistent interfaces across different service integrations
- Easy extensibility to add new service integrations
- Runtime discovery and registration of plugins
- Centralized access to plugin capabilities

Plugin Lifecycle:
---------------
1. Plugin classes are defined in separate modules
2. Plugins are registered with the registry using the registration functions
3. The application discovers and loads plugins at startup
4. Plugin instances are created when needed for specific operations
5. The application uses plugins through their defined interfaces

Adding a New Plugin:
------------------
To add support for a new service:
1. Create a new directory under 'plugins/'
2. Implement an AuthorizationPlugin for authentication
3. Implement a ResourcePlugin for API interactions
4. Register the plugins in the __init__.py of your plugin package
"""

from typing import Dict, List, Type, TypeVar, Optional, Any
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar('T', bound='PluginBase')
AuthPlugin = TypeVar('AuthPlugin', bound='AuthorizationPlugin')
ResourcePlugin = TypeVar('ResourcePlugin', bound='ResourcePlugin')
RoutePlugin = TypeVar('RoutePlugin', bound='RoutePlugin')

class PluginType(str, Enum):
    """
    Enum defining the types of plugins supported by the system.
    
    This classification helps with plugin discovery, management, and routing
    requests to the appropriate plugin type.
    
    Types:
        AUTHORIZATION: Plugins that handle authentication with resource servers
        RESOURCE: Plugins that interact with resource server APIs
        ROUTE: Plugins that provide HTTP endpoints
    """
    AUTHORIZATION = "authorization"
    RESOURCE = "resource"
    ROUTE = "route"

class PluginBase:
    """
    Base class for all plugins in the OAuth3 TEE Proxy system.
    
    This abstract base class defines the common interface and properties that all 
    plugins must implement. It provides a foundation for plugin identification
    and metadata retrieval.
    
    Class Attributes:
        plugin_type (PluginType): The type of plugin (AUTHORIZATION or RESOURCE)
        service_name (str): Unique identifier for the service this plugin supports
                           (e.g., "twitter", "telegram")
    """
    
    plugin_type: PluginType
    service_name: str
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """
        Return metadata about the plugin for discovery and introspection.
        
        This method provides standardized metadata about the plugin that can be
        used for plugin discovery, management, and UI presentation.
        
        Returns:
            Dict[str, Any]: Dictionary containing plugin metadata including:
                - plugin_type: The type of plugin
                - service_name: The service this plugin supports
                - class_name: The name of the plugin class
        """
        return {
            "plugin_type": cls.plugin_type,
            "service_name": cls.service_name,
            "class_name": cls.__name__
        }

class AuthorizationPlugin(PluginBase):
    """
    Base class for authorization plugins that handle authentication with resource servers.
    
    Authorization plugins are responsible for:
    - Validating and managing credentials for a specific service
    - Converting credentials between different formats
    - Extracting user identifiers from credentials
    - Handling the authentication flow for a service
    
    Implementations should handle the specific authentication mechanisms of their
    target service, such as OAuth2, API keys, cookies, or custom auth schemes.
    
    Class Attributes:
        plugin_type (PluginType): Set to AUTHORIZATION for all auth plugins
    """
    
    plugin_type = PluginType.AUTHORIZATION
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate if the credentials are valid and can be used to access the service.
        
        This method should make a lightweight API call to the service to check
        if the credentials are still valid and have not expired or been revoked.
        
        Args:
            credentials (Dict[str, Any]): The credentials to validate in dictionary form
            
        Returns:
            bool: True if credentials are valid, False otherwise
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement validate_credentials")
    
    async def get_user_identifier(self, credentials: Dict[str, Any]) -> str:
        """
        Extract a unique user identifier from the credentials.
        
        This method should extract a stable and unique identifier for the user
        from the credentials, such as a user ID, username, or account number.
        This identifier will be used to link the credentials to a specific user
        in the system.
        
        Args:
            credentials (Dict[str, Any]): The credentials to extract the identifier from
            
        Returns:
            str: A unique identifier for the user
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement get_user_identifier")
    
    def credentials_to_string(self, credentials: Dict[str, Any]) -> str:
        """
        Convert credentials dictionary to a string representation for storage.
        
        This method should serialize the credentials dictionary to a string format
        that can be safely stored in a database and later deserialized back
        into the original format.
        
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
        
        This method should deserialize the string representation of credentials
        back into the original dictionary format that can be used by the plugin.
        
        Args:
            credentials_str (str): String representation of credentials
            
        Returns:
            Dict[str, Any]: The deserialized credentials
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement credentials_from_string")

class ResourcePlugin(PluginBase):
    """
    Base class for resource plugins that interact with resource server APIs.
    
    Resource plugins are responsible for:
    - Initializing API clients with credentials
    - Performing operations against resource server APIs
    - Defining the available scopes and permissions
    - Managing resource-specific client state
    
    Implementations should handle the specific API interactions required for their
    target service, encapsulating all service-specific logic.
    
    Class Attributes:
        plugin_type (PluginType): Set to RESOURCE for all resource plugins
    """
    
    plugin_type = PluginType.RESOURCE
    
    async def initialize_client(self, credentials: Dict[str, Any]) -> Any:
        """
        Initialize an API client for the resource server using the provided credentials.
        
        This method should create and configure a client that can be used to make
        API calls to the resource server. The client should be initialized with
        the provided credentials.
        
        Args:
            credentials (Dict[str, Any]): The credentials to use for initialization
            
        Returns:
            Any: An initialized client object that can be used for API calls
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement initialize_client")
    
    async def validate_client(self, client: Any) -> bool:
        """
        Validate if the client is still valid and can be used for API calls.
        
        This method should check if the client's credentials are still valid
        and the client can be used to make API calls to the resource server.
        
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
        Get the list of scopes (permissions) supported by this resource plugin.
        
        This method should return a list of scope strings that define the
        permissions that can be granted for access to the resource server.
        These scopes will be used in the OAuth2 authorization flow.
        
        Returns:
            List[str]: List of scope strings (e.g., ["tweet.post", "tweet.read"])
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement get_available_scopes")

class RoutePlugin(PluginBase):
    """
    Base class for plugins that provide their own routes.
    
    Route plugins are responsible for:
    - Creating and configuring FastAPI APIRouter objects
    - Defining routes specific to their service
    - Handling HTTP requests for their service-specific endpoints
    - Implementing the necessary route handlers
    - Specifying authentication requirements for their routes
    
    The routes provided by a plugin are mounted under the service name,
    e.g., "/[service]/..." to create appropriate namespacing.
    
    Implementations should define service-specific routes and handlers,
    following the pattern used in the application.
    
    Class Attributes:
        plugin_type (PluginType): Set to ROUTE for all route plugins
    """
    
    plugin_type = PluginType.ROUTE
    
    def get_router(self):
        """
        Get the router for this plugin's routes.
        
        This method should return a FastAPI APIRouter object that defines
        all the routes for this plugin. The router will be mounted under
        the service name to create appropriate namespacing.
        
        Returns:
            fastapi.APIRouter: The router with all plugin-specific routes
            
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement get_router")
        
    def get_auth_requirements(self) -> Dict[str, List[str]]:
        """
        Get authentication requirements for this plugin's routes.
        
        This method should return a dictionary mapping route patterns to
        the authentication types required for those routes. Each route pattern
        can be an exact path or a wildcard pattern (ending with *).
        
        Example:
            {
                "/exact/path": ["session"],
                "/api/v1/*": ["oauth2", "session"],
                "/public/*": ["none"]
            }
        
        Returns:
            Dict[str, List[str]]: Dictionary mapping route patterns to required auth types
        """
        # Default implementation - no special auth requirements
        return {}

# Create directories if needed
import os
os.makedirs(os.path.dirname(__file__), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "twitter"), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "telegram"), exist_ok=True)

# Plugin registry
_authorization_plugins: Dict[str, Type[AuthorizationPlugin]] = {}
_resource_plugins: Dict[str, Type[ResourcePlugin]] = {}
_route_plugins: Dict[str, Type[RoutePlugin]] = {}

def register_authorization_plugin(plugin_class: Type[AuthorizationPlugin]) -> None:
    """
    Register an authorization plugin with the system.
    
    This function registers an AuthorizationPlugin subclass in the plugin registry,
    making it available for discovery and use by the application. Each plugin is
    registered under its service_name, which must be unique across all authorization
    plugins.
    
    Args:
        plugin_class (Type[AuthorizationPlugin]): The authorization plugin class to register
        
    Returns:
        None
        
    Example:
        >>> class MyAuthPlugin(AuthorizationPlugin):
        ...     service_name = "my_service"
        ...     # Implementation...
        >>> register_authorization_plugin(MyAuthPlugin)
    """
    _authorization_plugins[plugin_class.service_name] = plugin_class
    logger.info(f"Registered authorization plugin: {plugin_class.service_name}")

def register_resource_plugin(plugin_class: Type[ResourcePlugin]) -> None:
    """
    Register a resource plugin with the system.
    
    This function registers a ResourcePlugin subclass in the plugin registry,
    making it available for discovery and use by the application. Each plugin is
    registered under its service_name, which must be unique across all resource
    plugins.
    
    Args:
        plugin_class (Type[ResourcePlugin]): The resource plugin class to register
        
    Returns:
        None
        
    Example:
        >>> class MyResourcePlugin(ResourcePlugin):
        ...     service_name = "my_service"
        ...     # Implementation...
        >>> register_resource_plugin(MyResourcePlugin)
    """
    _resource_plugins[plugin_class.service_name] = plugin_class
    logger.info(f"Registered resource plugin: {plugin_class.service_name}")

def get_authorization_plugin(service_name: str) -> Optional[Type[AuthorizationPlugin]]:
    """
    Get an authorization plugin class by its service name.
    
    Retrieves a registered authorization plugin class from the registry using its
    service name. Returns None if no plugin with the given service name is found.
    
    Args:
        service_name (str): The unique service name of the plugin to retrieve
        
    Returns:
        Optional[Type[AuthorizationPlugin]]: The plugin class if found, None otherwise
        
    Example:
        >>> twitter_auth_plugin = get_authorization_plugin("twitter")
        >>> if twitter_auth_plugin:
        ...     plugin_instance = twitter_auth_plugin()
    """
    return _authorization_plugins.get(service_name)

def get_resource_plugin(service_name: str) -> Optional[Type[ResourcePlugin]]:
    """
    Get a resource plugin class by its service name.
    
    Retrieves a registered resource plugin class from the registry using its
    service name. Returns None if no plugin with the given service name is found.
    
    Args:
        service_name (str): The unique service name of the plugin to retrieve
        
    Returns:
        Optional[Type[ResourcePlugin]]: The plugin class if found, None otherwise
        
    Example:
        >>> twitter_resource_plugin = get_resource_plugin("twitter")
        >>> if twitter_resource_plugin:
        ...     plugin_instance = twitter_resource_plugin()
    """
    return _resource_plugins.get(service_name)

def get_all_authorization_plugins() -> Dict[str, Type[AuthorizationPlugin]]:
    """
    Get all registered authorization plugins.
    
    Returns a dictionary mapping service names to authorization plugin classes
    for all registered plugins. The dictionary is a copy of the internal registry,
    so modifying it will not affect the registry.
    
    Returns:
        Dict[str, Type[AuthorizationPlugin]]: Dictionary of all registered authorization plugins
        
    Example:
        >>> auth_plugins = get_all_authorization_plugins()
        >>> for name, plugin_class in auth_plugins.items():
        ...     print(f"Found auth plugin: {name}")
    """
    return _authorization_plugins.copy()

def get_all_resource_plugins() -> Dict[str, Type[ResourcePlugin]]:
    """
    Get all registered resource plugins.
    
    Returns a dictionary mapping service names to resource plugin classes
    for all registered plugins. The dictionary is a copy of the internal registry,
    so modifying it will not affect the registry.
    
    Returns:
        Dict[str, Type[ResourcePlugin]]: Dictionary of all registered resource plugins
        
    Example:
        >>> resource_plugins = get_all_resource_plugins()
        >>> for name, plugin_class in resource_plugins.items():
        ...     print(f"Found resource plugin: {name}")
    """
    return _resource_plugins.copy()

def get_all_route_plugins() -> Dict[str, Type[RoutePlugin]]:
    """
    Get all registered route plugins.
    
    Returns a dictionary mapping service names to route plugin classes
    for all registered plugins. The dictionary is a copy of the internal registry,
    so modifying it will not affect the registry.
    
    Returns:
        Dict[str, Type[RoutePlugin]]: Dictionary of all registered route plugins
        
    Example:
        >>> route_plugins = get_all_route_plugins()
        >>> for name, plugin_class in route_plugins.items():
        ...     print(f"Found route plugin: {name}")
    """
    return _route_plugins.copy()

def register_route_plugin(plugin_class: Type[RoutePlugin]) -> None:
    """
    Register a route plugin with the system.
    
    This function registers a RoutePlugin subclass in the plugin registry,
    making it available for discovery and use by the application. Each plugin is
    registered under its service_name, which must be unique across all route
    plugins.
    
    Args:
        plugin_class (Type[RoutePlugin]): The route plugin class to register
        
    Returns:
        None
        
    Example:
        >>> class MyRoutePlugin(RoutePlugin):
        ...     service_name = "my_service"
        ...     # Implementation...
        >>> register_route_plugin(MyRoutePlugin)
    """
    _route_plugins[plugin_class.service_name] = plugin_class
    logger.info(f"Registered route plugin: {plugin_class.service_name}")

def get_route_plugin(service_name: str) -> Optional[Type[RoutePlugin]]:
    """
    Get a route plugin class by its service name.
    
    Retrieves a registered route plugin class from the registry using its
    service name. Returns None if no plugin with the given service name is found.
    
    Args:
        service_name (str): The unique service name of the plugin to retrieve
        
    Returns:
        Optional[Type[RoutePlugin]]: The plugin class if found, None otherwise
        
    Example:
        >>> twitter_route_plugin = get_route_plugin("twitter")
        >>> if twitter_route_plugin:
        ...     plugin_instance = twitter_route_plugin()
    """
    return _route_plugins.get(service_name)

def get_all_authorization_plugin_classes() -> Dict[str, Type[AuthorizationPlugin]]:
    """
    Get all registered authorization plugin classes (for backward compatibility).
    
    This is an alias for get_all_authorization_plugins() provided for backward
    compatibility with older code.
    
    Returns:
        Dict[str, Type[AuthorizationPlugin]]: Dictionary of all registered authorization plugins
    """
    return get_all_authorization_plugins()
    
def get_all_resource_plugin_classes() -> Dict[str, Type[ResourcePlugin]]:
    """
    Get all registered resource plugin classes (for backward compatibility).
    
    This is an alias for get_all_resource_plugins() provided for backward
    compatibility with older code.
    
    Returns:
        Dict[str, Type[ResourcePlugin]]: Dictionary of all registered resource plugins
    """
    return get_all_resource_plugins()

def get_all_route_plugin_classes() -> Dict[str, Type[RoutePlugin]]:
    """
    Get all registered route plugin classes (for backward compatibility).
    
    This is an alias for get_all_route_plugins() provided for backward
    compatibility with older code.
    
    Returns:
        Dict[str, Type[RoutePlugin]]: Dictionary of all registered route plugins
    """
    return get_all_route_plugins()