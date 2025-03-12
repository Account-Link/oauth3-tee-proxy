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
    def get_plugin_info(request = None, twitter_accounts = None):
        """
        Get information about the Twitter plugin for display in the UI.
        
        Args:
            request: The HTTP request object (optional)
            twitter_accounts: List of Twitter accounts to display (optional)
            
        Returns:
            dict: Plugin metadata including description, features, and URLs
        """
        twitter_info = {
            "description": "Connect to Twitter and interact with its API using OAuth3 TEE Proxy.",
            "features": [
                "Authenticate using browser cookies or OAuth",
                "Post tweets and interact with Twitter content",
                "Execute GraphQL queries against Twitter's internal API",
                "Access Twitter's v1.1 REST API"
            ],
            "urls": {},  # Removed buttons as requested
            "color": "#1DA1F2",
            "icon": "twitter"
        }
        
        # Always include account count, even if zero
        twitter_info["account_count"] = len(twitter_accounts) if twitter_accounts else 0
        
        # If Twitter accounts are provided, include them in the plugin info
        if twitter_accounts and len(twitter_accounts) > 0:
            # Check which accounts have OAuth credentials
            account_oauth_status = {}
            
            try:
                from database import get_db
                from plugins.twitter.models import TwitterOAuthCredential
                
                # Get database session
                db = next(get_db())
                
                # Check OAuth status for each account
                for account in twitter_accounts:
                    oauth_cred = db.query(TwitterOAuthCredential).filter(
                        TwitterOAuthCredential.twitter_account_id == account.twitter_id
                    ).first()
                    account_oauth_status[account.twitter_id] = oauth_cred is not None
            except Exception as e:
                # If there's an error, continue without OAuth status
                pass
            
            # Render the account management component and include it
            template = templates.env.get_template("plugin_info.html")
            accounts_html = template.module.account_management(twitter_accounts, account_oauth_status)
            twitter_info["accounts_html"] = accounts_html
        
        return twitter_info
    
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
        # Check which accounts have OAuth credentials
        from database import get_db
        from plugins.twitter.models import TwitterOAuthCredential
        
        account_oauth_status = {}
        if twitter_accounts:
            # Get database session
            try:
                db = next(get_db())
                # Check OAuth status for each account
                for account in twitter_accounts:
                    oauth_cred = db.query(TwitterOAuthCredential).filter(
                        TwitterOAuthCredential.twitter_account_id == account.twitter_id
                    ).first()
                    account_oauth_status[account.twitter_id] = oauth_cred is not None
            except Exception as e:
                # If there's an error, continue without OAuth status
                pass
        
        # Get the template and call the account_management macro with accounts and OAuth status
        template = templates.env.get_template("plugin_info.html")
        return template.module.account_management(twitter_accounts, account_oauth_status)
    
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
    
# Removed duplicate get_plugin_info method
        
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
        
    @staticmethod
    def render_auth_admin_page(request: Request):
        """
        Renders the Twitter authentication admin page with multiple auth options.
        
        Args:
            request: The HTTP request object
            
        Returns:
            TemplateResponse: The rendered authentication options page
        """
        from database import get_db
        from sqlalchemy.orm import Session
        from plugins.twitter.models import TwitterAccount, TwitterOAuthCredential
        
        # Get database session
        db = next(get_db())
        
        # Get user ID from session
        user_id = request.session.get("user_id")
        
        # Get Twitter accounts for user
        twitter_accounts = []
        account_oauth_status = {}
        
        if user_id:
            twitter_accounts = db.query(TwitterAccount).filter(
                TwitterAccount.user_id == user_id
            ).all()
            
            # Check which accounts have OAuth credentials
            for account in twitter_accounts:
                oauth_cred = db.query(TwitterOAuthCredential).filter(
                    TwitterOAuthCredential.twitter_account_id == account.twitter_id
                ).first()
                account_oauth_status[account.twitter_id] = oauth_cred is not None
        
        return templates.TemplateResponse(
            "twitter_auth_admin.html",
            {
                "request": request,
                "twitter_accounts": twitter_accounts,
                "account_oauth_status": account_oauth_status
            }
        )

# Create a singleton instance of the UI provider
twitter_ui = TwitterUIProvider()