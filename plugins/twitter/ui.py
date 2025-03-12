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
main_template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=template_dir)
# Add the main templates directory to Jinja loader to find base.html
templates.env.loader.searchpath.append(main_template_dir)

class TwitterUIProvider:
    """Provides UI components for the Twitter plugin."""
    
    @staticmethod
    def get_plugin_info(request = None):
        """
        Get information about the Twitter plugin for display in the UI.
        
        Args:
            request: The HTTP request object (optional)
            
        Returns:
            dict: Plugin metadata including description, features, and URLs
        """
        # This is already returning a dict directly, not using a template, so no change needed
        return {
            "description": "Connect to Twitter and interact with its API using OAuth3 TEE Proxy.",
            "features": [
                "Authenticate using browser cookies or OAuth",
                "Post tweets and interact with Twitter content",
                "Execute GraphQL queries against Twitter's internal API",
                "Access Twitter's v1.1 REST API"
            ],
            "urls": {
                "GraphQL Playground": "/twitter/graphql/playground",
                "Add Account": "/twitter/submit-cookie",
                "Documentation": "https://developer.twitter.com/en/docs"
            },
            "color": "#1DA1F2",
            "icon": "twitter"
        }
    
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
        # Get the template and call the account_management macro directly with the accounts
        template = templates.env.get_template("plugin_info.html")
        return template.module.account_management(twitter_accounts)
    
    @staticmethod
    def get_dashboard_actions(request: Request):
        """
        Returns HTML for Twitter-specific action buttons on the dashboard.
        
        Args:
            request: The HTTP request object
        
        Returns:
            str: HTML for Twitter action buttons
        """
        template = templates.env.get_template("plugin_info.html")
        return template.module.dashboard_actions()
    
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