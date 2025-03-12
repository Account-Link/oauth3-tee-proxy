# plugin_manager.py
"""
Plugin Manager for OAuth3 TEE Proxy
===================================

This module provides utilities for discovering, loading, and managing plugins in the
OAuth3 TEE Proxy system. It serves as the central coordination point for plugin
operations, handling plugin discovery, registration, and access.

The PluginManager class provides a facade over the lower-level plugin registry,
offering simplified access to plugins and plugin capabilities. It handles the
complexity of plugin lifecycle management, making it easier for the application
to work with plugins.

Key capabilities:
- Dynamic discovery of plugins at runtime
- Creation of plugin instances
- Access to plugin metadata and capabilities
- Aggregation of plugin-provided scopes
- Centralized error handling for plugin operations

Usage:
------
The plugin_manager is instantiated as a singleton at the module level and should be
imported and used directly by application code:

    from plugin_manager import plugin_manager
    
    # Discover available plugins
    plugin_manager.discover_plugins()
    
    # Get a plugin by name
    twitter_auth = plugin_manager.create_authorization_plugin("twitter")
    
    # Get all available scopes from all plugins
    scopes = plugin_manager.get_all_plugin_scopes()
"""

import importlib
import logging
import os
from typing import Dict, List, Type, Optional, Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from plugins import (
    AuthorizationPlugin,
    ResourcePlugin,
    RoutePlugin,
    get_authorization_plugin,
    get_resource_plugin,
    get_route_plugin,
    get_all_authorization_plugin_classes,
    get_all_resource_plugin_classes,
    get_all_route_plugin_classes
)

logger = logging.getLogger(__name__)

class PluginManager:
    """
    Manager for OAuth3 TEE Proxy plugins.
    
    This class provides a central point for discovering, accessing, and managing
    plugins in the OAuth3 TEE Proxy system. It handles plugin discovery,
    instantiation, and capability aggregation, offering a simplified interface
    for working with plugins.
    
    The PluginManager is responsible for:
    - Discovering plugins in the plugins directory
    - Loading plugin modules
    - Creating plugin instances
    - Providing access to plugin capabilities
    - Aggregating plugin-provided scopes
    
    It acts as a facade over the lower-level plugin registry, providing a more
    user-friendly interface for working with plugins.
    """
    
    def __init__(self):
        """
        Initialize the plugin manager.
        
        Sets up the plugin manager with the path to the plugins directory and
        initializes tracking for loaded plugin modules. Plugins are not loaded
        during initialization; the discover_plugins method must be called to
        discover and load plugins.
        """
        self._plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self._loaded_plugins = set()
        self._plugin_ui_providers = {}
    
    def discover_plugins(self):
        """
        Discover plugins in the plugins directory.
        
        This method scans the plugins directory for plugin packages (subdirectories)
        and attempts to import each package. Each successfully imported package
        is expected to register its plugins with the plugin registry.
        
        The method tracks which plugin modules have been loaded to avoid
        loading the same module multiple times. It logs information about
        discovered plugins and any errors that occur during loading.
        
        Returns:
            None
        """
        for item in os.listdir(self._plugin_dir):
            if os.path.isdir(os.path.join(self._plugin_dir, item)) and not item.startswith('__'):
                module_name = f"plugins.{item}"
                if module_name not in self._loaded_plugins:
                    try:
                        module = importlib.import_module(module_name)
                        self._loaded_plugins.add(module_name)
                        logger.info(f"Discovered plugin: {module_name}")
                        
                        # Try to load UI provider if available
                        try:
                            ui_module = importlib.import_module(f"{module_name}.ui")
                            if hasattr(ui_module, f"{item}_ui"):
                                self._plugin_ui_providers[item] = getattr(ui_module, f"{item}_ui")
                                logger.info(f"Loaded UI provider for plugin: {item}")
                        except ImportError:
                            # UI module is optional, so this is not an error
                            pass
                    except ImportError as e:
                        logger.error(f"Error loading plugin {module_name}: {e}")
    
    def get_authorization_plugin(self, service_name: str) -> Optional[Type[AuthorizationPlugin]]:
        """
        Get an authorization plugin class by service name.
        
        Retrieves a registered authorization plugin class from the registry using its
        service name. Returns None if no plugin with the given service name is found.
        
        Args:
            service_name (str): The unique service name of the plugin to retrieve
            
        Returns:
            Optional[Type[AuthorizationPlugin]]: The plugin class if found, None otherwise
        """
        from plugins import get_authorization_plugin
        return get_authorization_plugin(service_name)
    
    def get_resource_plugin(self, service_name: str) -> Optional[Type[ResourcePlugin]]:
        """
        Get a resource plugin class by service name.
        
        Retrieves a registered resource plugin class from the registry using its
        service name. Returns None if no plugin with the given service name is found.
        
        Args:
            service_name (str): The unique service name of the plugin to retrieve
            
        Returns:
            Optional[Type[ResourcePlugin]]: The plugin class if found, None otherwise
        """
        from plugins import get_resource_plugin
        return get_resource_plugin(service_name)
    
    def get_all_authorization_plugins(self) -> Dict[str, Type[AuthorizationPlugin]]:
        """
        Get all registered authorization plugins.
        
        Returns a dictionary mapping service names to authorization plugin classes
        for all registered plugins. The dictionary is a copy of the internal registry,
        so modifying it will not affect the registry.
        
        Returns:
            Dict[str, Type[AuthorizationPlugin]]: Dictionary of all registered authorization plugins
        """
        from plugins import get_all_authorization_plugins
        return get_all_authorization_plugins()
    
    def get_all_resource_plugins(self) -> Dict[str, Type[ResourcePlugin]]:
        """
        Get all registered resource plugins.
        
        Returns a dictionary mapping service names to resource plugin classes
        for all registered plugins. The dictionary is a copy of the internal registry,
        so modifying it will not affect the registry.
        
        Returns:
            Dict[str, Type[ResourcePlugin]]: Dictionary of all registered resource plugins
        """
        from plugins import get_all_resource_plugins
        return get_all_resource_plugins()
    
    def create_authorization_plugin(self, service_name: str, **kwargs) -> Optional[AuthorizationPlugin]:
        """
        Create an instance of an authorization plugin.
        
        Creates and returns an instance of the authorization plugin with the given
        service name, passing any additional keyword arguments to the plugin's
        constructor. Returns None if no plugin with the given service name is found.
        
        Args:
            service_name (str): The unique service name of the plugin to instantiate
            **kwargs: Additional keyword arguments to pass to the plugin constructor
            
        Returns:
            Optional[AuthorizationPlugin]: A plugin instance if the plugin was found,
                                          None otherwise
                                          
        Example:
            >>> twitter_auth = plugin_manager.create_authorization_plugin("twitter")
            >>> if twitter_auth:
            ...     is_valid = await twitter_auth.validate_credentials(credentials)
        """
        plugin_class = self.get_authorization_plugin(service_name)
        if plugin_class:
            return plugin_class(**kwargs)
        return None
    
    def create_resource_plugin(self, service_name: str, **kwargs) -> Optional[ResourcePlugin]:
        """
        Create an instance of a resource plugin.
        
        Creates and returns an instance of the resource plugin with the given
        service name, passing any additional keyword arguments to the plugin's
        constructor. Returns None if no plugin with the given service name is found.
        
        Args:
            service_name (str): The unique service name of the plugin to instantiate
            **kwargs: Additional keyword arguments to pass to the plugin constructor
            
        Returns:
            Optional[ResourcePlugin]: A plugin instance if the plugin was found,
                                     None otherwise
                                     
        Example:
            >>> twitter_resource = plugin_manager.create_resource_plugin("twitter")
            >>> if twitter_resource:
            ...     client = await twitter_resource.initialize_client(credentials)
        """
        plugin_class = self.get_resource_plugin(service_name)
        if plugin_class:
            return plugin_class(**kwargs)
        return None
    
    def get_all_plugin_scopes(self) -> Dict[str, str]:
        """
        Get all scopes from all resource plugins.
        
        Collects and returns all available scopes from all registered resource plugins,
        along with their descriptions. This method instantiates each resource plugin
        to retrieve its available scopes, merging them into a single dictionary.
        
        Returns:
            Dict[str, str]: Dictionary mapping scope names to scope descriptions
            
        Example:
            >>> scopes = plugin_manager.get_all_plugin_scopes()
            >>> for scope, description in scopes.items():
            ...     print(f"{scope}: {description}")
        """
        scopes = {}
        for plugin_name, plugin_class in self.get_all_resource_plugins().items():
            plugin = plugin_class()
            for scope in plugin.get_available_scopes():
                if hasattr(plugin_class, 'SCOPES') and scope in plugin_class.SCOPES:
                    scopes[scope] = plugin_class.SCOPES[scope]
                else:
                    scopes[scope] = f"Permission for {scope}"
        return scopes
        
    def get_all_route_plugins(self) -> Dict[str, Type[RoutePlugin]]:
        """
        Get all registered route plugins.
        
        Returns a dictionary mapping service names to route plugin classes
        for all registered plugins.
        
        Returns:
            Dict[str, Type[RoutePlugin]]: Dictionary of all registered route plugins
        """
        from plugins import get_all_route_plugin_classes
        return get_all_route_plugin_classes()
    
    def create_route_plugin(self, service_name: str, **kwargs) -> Optional[RoutePlugin]:
        """
        Create an instance of a route plugin.
        
        Creates and returns an instance of the route plugin with the given
        service name, passing any additional keyword arguments to the plugin's
        constructor. Returns None if no plugin with the given service name is found.
        
        Args:
            service_name (str): The unique service name of the plugin to instantiate
            **kwargs: Additional keyword arguments to pass to the plugin constructor
            
        Returns:
            Optional[RoutePlugin]: A plugin instance if the plugin was found,
                                  None otherwise
        """
        from plugins import get_route_plugin
        plugin_class = get_route_plugin(service_name)
        if plugin_class:
            return plugin_class(**kwargs)
        return None
    
    def get_service_routers(self) -> Dict[str, APIRouter]:
        """
        Get all routers from plugins that implement the RoutePlugin interface.
        
        This method identifies plugins that implement the RoutePlugin interface,
        instantiates them, and calls their get_router() method to retrieve the
        service-specific routers. The routers are keyed by service name for
        mounting in the main application.
        
        Returns:
            Dict[str, APIRouter]: Dictionary mapping service names to their routers
            
        Example:
            >>> routers = plugin_manager.get_service_routers()
            >>> for service_name, router in routers.items():
            ...     app.include_router(router, prefix=f"/{service_name}")
        """
        routers = {}
        
        # Get all dedicated route plugins
        for service_name, plugin_class in self.get_all_route_plugins().items():
            plugin = plugin_class()
            routers[service_name] = plugin.get_router()
            logger.info(f"Found route plugin: {service_name}")
        
        # Check authorization plugins that also implement RoutePlugin
        for service_name, plugin_class in self.get_all_authorization_plugins().items():
            if issubclass(plugin_class, RoutePlugin) and service_name not in routers:
                plugin = plugin_class()
                routers[service_name] = plugin.get_router()
                logger.info(f"Found route plugin in authorization plugin: {service_name}")
        
        # Check resource plugins that also implement RoutePlugin
        for service_name, plugin_class in self.get_all_resource_plugins().items():
            if issubclass(plugin_class, RoutePlugin) and service_name not in routers:
                plugin = plugin_class()
                routers[service_name] = plugin.get_router()
                logger.info(f"Found route plugin in resource plugin: {service_name}")
        
        return routers
        
    def get_plugin_ui(self, plugin_name: str) -> Optional[Any]:
        """
        Get the UI provider for a specific plugin.
        
        UI providers allow plugins to contribute UI components to the main application.
        They typically provide methods to render templates or components for different
        parts of the UI.
        
        Args:
            plugin_name (str): The name of the plugin
            
        Returns:
            Optional[Any]: The UI provider for the plugin, or None if not found
            
        Example:
            >>> twitter_ui = plugin_manager.get_plugin_ui("twitter")
            >>> if twitter_ui:
            ...     dashboard_component = twitter_ui.get_dashboard_component(request, accounts)
        """
        return self._plugin_ui_providers.get(plugin_name)
        
    def get_all_plugin_uis(self) -> Dict[str, Any]:
        """
        Get all registered plugin UI providers.
        
        Returns a dictionary mapping plugin names to their UI providers.
        
        Returns:
            Dict[str, Any]: Dictionary of all registered plugin UI providers
        """
        return self._plugin_ui_providers.copy()
        
    def get_plugin_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available plugins.
        
        This method collects metadata about all registered plugins, including:
        - Plugin name and description
        - Available actions or UI components
        - Configuration options
        - Support status
        
        If a plugin has a UI provider with a get_plugin_info method, that method
        is called to get additional plugin information.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping plugin names to their metadata
        """
        plugin_info = {}
        
        try:
            # Get all resource plugins
            for service_name, plugin_class in self.get_all_resource_plugins().items():
                try:
                    # Create base info for the plugin
                    info = {
                        "name": service_name,
                        "description": f"Integration with {service_name.title()}",
                        "type": "resource",
                        "urls": {}
                    }
                    
                    # Try to get description from plugin class
                    if hasattr(plugin_class, "DESCRIPTION"):
                        info["description"] = getattr(plugin_class, "DESCRIPTION")
                    
                    # Add plugin-specific URLs
                    if service_name == "twitter":
                        info["urls"] = {
                            "Add Account": "/submit-cookie"
                        }
                    elif service_name == "twitter_graphql":
                        info["urls"] = {
                            "GraphQL Playground": "/twitter/graphql/playground"
                        }  
                    elif service_name == "telegram":
                        info["urls"] = {
                            "Add Account": "/add-telegram"
                        }
                    
                    # Check if plugin has a UI provider with get_plugin_info method
                    ui_provider = self._plugin_ui_providers.get(service_name)
                    if ui_provider:
                        if hasattr(ui_provider, "get_plugin_info"):
                            try:
                                # Merge with UI provider info
                                ui_info = ui_provider.get_plugin_info()
                                if isinstance(ui_info, dict):
                                    info.update(ui_info)
                            except Exception as e:
                                logger.error(f"Error getting UI info for plugin {service_name}: {e}")
                    
                    plugin_info[service_name] = info
                except Exception as e:
                    logger.error(f"Error processing plugin info for {service_name}: {e}")
                    # Add minimal info for the plugin if we couldn't get full info
                    plugin_info[service_name] = {
                        "name": service_name,
                        "description": f"Integration with {service_name.title()}",
                        "type": "resource",
                        "urls": {}
                    }
            
            return plugin_info
        except Exception as e:
            logger.error(f"Error in get_plugin_info: {e}")
            return {}
        
    def render_dashboard_components(self, request: Request, context: Dict[str, Any]) -> List[str]:
        """
        Render dashboard components from all plugins.
        
        This method calls the get_dashboard_component method on all registered
        UI providers, passing the request and relevant context data, and returns
        a list of HTML strings for inclusion in the dashboard template.
        
        Args:
            request (Request): The HTTP request
            context (Dict[str, Any]): The template context data
            
        Returns:
            List[str]: HTML strings for dashboard components
        """
        components = []
        
        try:
            # Safely iterate through UI providers
            for plugin_name, ui_provider in self._plugin_ui_providers.items():
                if not ui_provider or not hasattr(ui_provider, "get_dashboard_component"):
                    continue
                
                try:
                    # Get plugin-specific context data
                    plugin_context = {}
                    if plugin_name == "twitter" and "twitter_accounts" in context:
                        plugin_context = {"twitter_accounts": context.get("twitter_accounts", [])}
                    elif plugin_name == "telegram" and "telegram_accounts" in context:
                        plugin_context = {"telegram_accounts": context.get("telegram_accounts", [])}
                    
                    # Render the component
                    component = ui_provider.get_dashboard_component(request, **plugin_context)
                    if component and isinstance(component, str):
                        components.append(component)
                except Exception as e:
                    logger.error(f"Error rendering dashboard component for plugin {plugin_name}: {e}")
                    # Include fallback component for the plugin if rendering fails
                    fallback = f"""
                    <div class="dashboard-section">
                        <h2>{plugin_name.title()} Accounts</h2>
                        <p>Unable to load accounts. Please try again later.</p>
                    </div>
                    """
                    components.append(fallback)
        except Exception as e:
            logger.error(f"Error in render_dashboard_components: {e}")
        
        return components

# Create a singleton instance of the plugin manager
plugin_manager = PluginManager()