"""
Twitter Plugin UI Components
===========================

This module provides UI components for the Twitter plugin, allowing the plugin
to integrate with the OAuth3 TEE Proxy's web interface.
"""

from fastapi import Request
from fastapi.templating import Jinja2Templates
import os

# Create a templates instance for the Twitter plugin
template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=template_dir)

class TwitterUIProvider:
    """Provides UI components for the Twitter plugin."""
    
    @staticmethod
    def get_dashboard_component(request: Request, twitter_accounts):
        """
        Returns HTML for the Twitter accounts component on the dashboard.
        
        Args:
            request: The HTTP request object
            twitter_accounts: List of TwitterAccount objects for the current user
        
        Returns:
            str: HTML for the Twitter accounts section
        """
        return templates.get_template("plugin_info.html").render(
            {"request": request, "twitter_accounts": twitter_accounts},
            block_name="account_management"
        )
    
    @staticmethod
    def get_dashboard_actions(request: Request):
        """
        Returns HTML for Twitter-specific action buttons on the dashboard.
        
        Args:
            request: The HTTP request object
        
        Returns:
            str: HTML for Twitter action buttons
        """
        return templates.get_template("plugin_info.html").render(
            {"request": request},
            block_name="dashboard_actions"
        )
    
    @staticmethod
    def get_plugin_info(request: Request):
        """
        Returns HTML describing the Twitter plugin capabilities.
        
        Args:
            request: The HTTP request object
        
        Returns:
            str: HTML with plugin information
        """
        return templates.get_template("plugin_info.html").render(
            {"request": request},
            block_name="plugin_info"
        )
        
    @staticmethod
    def render_graphql_playground(request: Request, oauth2_tokens, operations):
        """
        Renders the Twitter GraphQL playground page.
        
        Args:
            request: The HTTP request object
            oauth2_tokens: List of OAuth2Token objects for the current user
            operations: Dictionary of available GraphQL operations
            
        Returns:
            TemplateResponse: The rendered GraphQL playground page
        """
        return templates.TemplateResponse(
            "graphql_playground.html",
            {
                "request": request,
                "oauth2_tokens": oauth2_tokens,
                "operations": operations
            }
        )
        
    @staticmethod
    def render_submit_cookie_page(request: Request):
        """
        Renders the Twitter cookie submission page.
        
        Args:
            request: The HTTP request object
            
        Returns:
            TemplateResponse: The rendered cookie submission page
        """
        return templates.TemplateResponse(
            "submit_cookie.html",
            {"request": request}
        )

# Create a singleton instance of the UI provider
twitter_ui = TwitterUIProvider()