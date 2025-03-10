# plugin_manager.py
"""
Plugin manager for OAuth3 TEE Proxy.

This module provides utilities for discovering, loading, and managing plugins.
It handles plugin registration and provides a central point for accessing plugins.
"""

import importlib
import logging
import os
from typing import Dict, List, Type, Optional, Any

from plugins import (
    AuthorizationPlugin,
    ResourcePlugin,
    get_authorization_plugin,
    get_resource_plugin,
    get_all_authorization_plugin_classes,
    get_all_resource_plugin_classes
)

logger = logging.getLogger(__name__)

class PluginManager:
    """Manager for OAuth3 TEE Proxy plugins."""
    
    def __init__(self):
        """Initialize the plugin manager."""
        self._plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self._loaded_plugins = set()
    
    def discover_plugins(self):
        """Discover plugins in the plugins directory."""
        for item in os.listdir(self._plugin_dir):
            if os.path.isdir(os.path.join(self._plugin_dir, item)) and not item.startswith('__'):
                module_name = f"plugins.{item}"
                if module_name not in self._loaded_plugins:
                    try:
                        importlib.import_module(module_name)
                        self._loaded_plugins.add(module_name)
                        logger.info(f"Discovered plugin: {module_name}")
                    except ImportError as e:
                        logger.error(f"Error loading plugin {module_name}: {e}")
    
    def get_authorization_plugin(self, service_name: str) -> Optional[Type[AuthorizationPlugin]]:
        """Get an authorization plugin by service name."""
        return get_authorization_plugin(service_name)
    
    def get_resource_plugin(self, service_name: str) -> Optional[Type[ResourcePlugin]]:
        """Get a resource plugin by service name."""
        return get_resource_plugin(service_name)
    
    def get_all_authorization_plugins(self) -> Dict[str, Type[AuthorizationPlugin]]:
        """Get all registered authorization plugins."""
        return get_all_authorization_plugins()
    
    def get_all_resource_plugins(self) -> Dict[str, Type[ResourcePlugin]]:
        """Get all registered resource plugins."""
        return get_all_resource_plugins()
    
    def create_authorization_plugin(self, service_name: str, **kwargs) -> Optional[AuthorizationPlugin]:
        """Create an instance of an authorization plugin."""
        plugin_class = self.get_authorization_plugin(service_name)
        if plugin_class:
            return plugin_class(**kwargs)
        return None
    
    def create_resource_plugin(self, service_name: str, **kwargs) -> Optional[ResourcePlugin]:
        """Create an instance of a resource plugin."""
        plugin_class = self.get_resource_plugin(service_name)
        if plugin_class:
            return plugin_class(**kwargs)
        return None
    
    def get_all_plugin_scopes(self) -> Dict[str, str]:
        """Get all scopes from all resource plugins."""
        scopes = {}
        for plugin_name, plugin_class in self.get_all_resource_plugins().items():
            plugin = plugin_class()
            for scope in plugin.get_available_scopes():
                if hasattr(plugin_class, 'SCOPES') and scope in plugin_class.SCOPES:
                    scopes[scope] = plugin_class.SCOPES[scope]
                else:
                    scopes[scope] = f"Permission for {scope}"
        return scopes

# Create a singleton instance of the plugin manager
plugin_manager = PluginManager()