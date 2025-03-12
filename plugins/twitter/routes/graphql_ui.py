"""
Twitter GraphQL UI Components
============================

This module provides UI components specific to the Twitter GraphQL plugin.
"""

import os
from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

# Set up templating
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
main_template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "templates")
templates = Jinja2Templates(directory=templates_dir)
# Add the main templates directory to Jinja loader to find base.html
templates.env.loader.searchpath.append(main_template_dir)

class TwitterGraphQLUIProvider:
    """Provides UI components for the Twitter GraphQL plugin."""
    
    @staticmethod
    def get_plugin_info(request: Request = None):
        """
        Returns metadata about the Twitter GraphQL plugin.
        
        Args:
            request: The HTTP request object (optional)
            
        Returns:
            dict: Plugin metadata
        """
        return {
            "description": "Execute GraphQL queries against Twitter's internal API.",
            "features": [
                "Access Twitter's internal GraphQL API",
                "Run predefined API operations",
                "Create custom GraphQL queries",
                "Test queries in an interactive playground"
            ],
            "urls": {
                "GraphQL Playground": "/twitter/graphql/playground"
            }
        }
    
    @staticmethod
    def render_graphql_playground(request: Request, oauth2_tokens, operations):
        """
        Renders the Twitter GraphQL playground page.
        
        Args:
            request: The HTTP request
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

# Create a singleton instance
twitter_graphql_ui = TwitterGraphQLUIProvider()