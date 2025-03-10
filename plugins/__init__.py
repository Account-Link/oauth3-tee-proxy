# plugins/__init__.py
"""
This module provides the plugin system for the OAuth3 TEE Proxy.
It defines base interfaces and plugin management functionality.
"""

from typing import Dict, List, Type, TypeVar, Optional, Any
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar('T', bound='PluginBase')
AuthPlugin = TypeVar('AuthPlugin', bound='AuthorizationPlugin')
ResourcePlugin = TypeVar('ResourcePlugin', bound='ResourcePlugin')

class PluginType(str, Enum):
    """Enum defining the types of plugins supported by the system."""
    AUTHORIZATION = "authorization"
    RESOURCE = "resource"

class PluginBase:
    """Base class for all plugins."""
    
    plugin_type: PluginType
    service_name: str
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Return metadata about the plugin."""
        return {
            "plugin_type": cls.plugin_type,
            "service_name": cls.service_name,
            "class_name": cls.__name__
        }

class AuthorizationPlugin(PluginBase):
    """Base class for authorization plugins that handle authentication with resource servers."""
    
    plugin_type = PluginType.AUTHORIZATION
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validate if the credentials are valid."""
        raise NotImplementedError("Subclasses must implement validate_credentials")
    
    async def get_user_identifier(self, credentials: Dict[str, Any]) -> str:
        """Get the user identifier from the credentials."""
        raise NotImplementedError("Subclasses must implement get_user_identifier")
    
    def credentials_to_string(self, credentials: Dict[str, Any]) -> str:
        """Convert credentials to a string representation for storage."""
        raise NotImplementedError("Subclasses must implement credentials_to_string")
    
    def credentials_from_string(self, credentials_str: str) -> Dict[str, Any]:
        """Convert a string representation back to credentials."""
        raise NotImplementedError("Subclasses must implement credentials_from_string")

class ResourcePlugin(PluginBase):
    """Base class for resource plugins that interact with resource server APIs."""
    
    plugin_type = PluginType.RESOURCE
    
    async def initialize_client(self, credentials: Dict[str, Any]) -> Any:
        """Initialize the client for the resource server."""
        raise NotImplementedError("Subclasses must implement initialize_client")
    
    async def validate_client(self, client: Any) -> bool:
        """Validate if the client is still valid."""
        raise NotImplementedError("Subclasses must implement validate_client")
    
    def get_available_scopes(self) -> List[str]:
        """Get the list of scopes supported by this resource plugin."""
        raise NotImplementedError("Subclasses must implement get_available_scopes")

# Create directories if needed
import os
os.makedirs(os.path.dirname(__file__), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "twitter"), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "telegram"), exist_ok=True)

# Plugin registry
_authorization_plugins: Dict[str, Type[AuthorizationPlugin]] = {}
_resource_plugins: Dict[str, Type[ResourcePlugin]] = {}

def register_authorization_plugin(plugin_class: Type[AuthorizationPlugin]) -> None:
    """Register an authorization plugin."""
    _authorization_plugins[plugin_class.service_name] = plugin_class
    logger.info(f"Registered authorization plugin: {plugin_class.service_name}")

def register_resource_plugin(plugin_class: Type[ResourcePlugin]) -> None:
    """Register a resource plugin."""
    _resource_plugins[plugin_class.service_name] = plugin_class
    logger.info(f"Registered resource plugin: {plugin_class.service_name}")

def get_authorization_plugin(service_name: str) -> Optional[Type[AuthorizationPlugin]]:
    """Get an authorization plugin by service name."""
    return _authorization_plugins.get(service_name)

def get_resource_plugin(service_name: str) -> Optional[Type[ResourcePlugin]]:
    """Get a resource plugin by service name."""
    return _resource_plugins.get(service_name)

def get_all_authorization_plugins() -> Dict[str, Type[AuthorizationPlugin]]:
    """Get all registered authorization plugins."""
    return _authorization_plugins.copy()

def get_all_resource_plugins() -> Dict[str, Type[ResourcePlugin]]:
    """Get all registered resource plugins."""
    return _resource_plugins.copy()

def get_all_authorization_plugin_classes() -> Dict[str, Type[AuthorizationPlugin]]:
    """Get all registered authorization plugin classes (for backward compatibility)."""
    return get_all_authorization_plugins()
    
def get_all_resource_plugin_classes() -> Dict[str, Type[ResourcePlugin]]:
    """Get all registered resource plugin classes (for backward compatibility)."""
    return get_all_resource_plugins()