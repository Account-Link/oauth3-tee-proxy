# Standard library imports
from datetime import datetime
import logging

# Third-party imports
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

# Local imports
from database import get_db
from models import User, OAuth2Token
from plugins.twitter.models import TwitterAccount
from plugins.telegram.models import TelegramAccount, TelegramChannel
from plugin_manager import plugin_manager

# Set up logging
logger = logging.getLogger(__name__)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Create router
router = APIRouter(tags=["UI:Dashboard"])

@router.get("/submit-cookie", response_class=HTMLResponse)
async def submit_cookie_page(request: Request):
    """
    Page for submitting Twitter cookie authentication.
    
    This route now uses the Twitter plugin's UI provider to render the template.
    """
    # Check if user is authenticated
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    
    try:
        # Get the Twitter UI provider and render the submit cookie page
        twitter_ui = plugin_manager.get_plugin_ui("twitter")
        if twitter_ui and hasattr(twitter_ui, "render_submit_cookie_page"):
            return twitter_ui.render_submit_cookie_page(request)
        
        # Fallback to the old template if the UI provider is not available
        return templates.TemplateResponse("submit_cookie.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering submit_cookie page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "An error occurred while loading the Twitter cookie form. Please try again later.",
            "back_url": "/dashboard"
        })

@router.get("/add-telegram", response_class=HTMLResponse)
async def add_telegram_page(request: Request):
    """Page for adding a Telegram account."""
    # Check if user is authenticated
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("add_telegram.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Main dashboard page showing connected accounts and OAuth tokens.
    
    This page displays all user's connected service accounts (Twitter, Telegram)
    and any active OAuth2 tokens issued to client applications.
    
    The dashboard now uses plugin UI components to render service-specific sections,
    making it more modular and extensible.
    """
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            request.session.clear()
            return RedirectResponse(url="/login")
        
        # Create the base context
        context = {
            "request": request,
            "user": user,
            "twitter_accounts": [],
            "telegram_accounts": [],
            "oauth2_tokens": [],
            "available_scopes": [],
            "available_plugins": {},
            "plugin_components": [],
            "plugin_actions": []
        }
        
        try:
            # Get accounts from enabled plugins
            # Check if Twitter plugin is available
            if any(plugin.service_name == "twitter" for plugin in plugin_manager.get_all_resource_plugins().values()):
                context["twitter_accounts"] = db.query(TwitterAccount).filter(
                    TwitterAccount.user_id == user_id
                ).all()
            
            # Check if Telegram plugin is available
            if any(plugin.service_name == "telegram" for plugin in plugin_manager.get_all_resource_plugins().values()):
                context["telegram_accounts"] = db.query(TelegramAccount).filter(
                    TelegramAccount.user_id == user_id
                ).all()
                
                # Get channels for each Telegram account
                for account in context["telegram_accounts"]:
                    account.channels = db.query(TelegramChannel).filter(
                        TelegramChannel.telegram_account_id == account.id
                    ).all()
        except Exception as e:
            logger.error(f"Error loading plugin accounts: {e}")
        
        try:
            # Get active OAuth2 tokens
            context["oauth2_tokens"] = db.query(OAuth2Token).filter(
                OAuth2Token.user_id == user_id,
                OAuth2Token.is_active == True,
                OAuth2Token.expires_at > datetime.utcnow()
            ).all()
        except Exception as e:
            logger.error(f"Error loading OAuth2 tokens: {e}")
        
        try:
            # Get all available scopes from plugins
            scopes = plugin_manager.get_all_plugin_scopes()
            context["available_scopes"] = scopes.keys()
        except Exception as e:
            logger.error(f"Error loading plugin scopes: {e}")
        
        try:
            # Get plugin information from plugin manager
            context["available_plugins"] = {}  # Start with empty dict
            try:
                # Attempt to get dynamic plugin info
                context["available_plugins"] = plugin_manager.get_plugin_info()
            except Exception as e:
                logger.error(f"Error getting plugin info: {e}")
                # Fallback to manual plugin info
                if any(plugin.service_name == "twitter" for plugin in plugin_manager.get_all_resource_plugins().values()):
                    context["available_plugins"]["twitter"] = {
                        "name": "twitter",
                        "description": "Connect to Twitter and use its API through OAuth3 TEE Proxy.",
                        "urls": {
                            "GraphQL Playground": "/graphql-playground",
                            "Add Account": "/submit-cookie"
                        }
                    }
                
                if any(plugin.service_name == "telegram" for plugin in plugin_manager.get_all_resource_plugins().values()):
                    context["available_plugins"]["telegram"] = {
                        "name": "telegram",
                        "description": "Access Telegram channels and messages through OAuth3 TEE Proxy.",
                        "urls": {
                            "Add Account": "/add-telegram"
                        }
                    }
        except Exception as e:
            logger.error(f"Error in plugin info fallback: {e}")
        
        try:
            # Render plugin-specific UI components
            components = []
            try:
                components = plugin_manager.render_dashboard_components(request, context)
            except Exception as e:
                logger.error(f"Error rendering plugin components: {e}")
            context["plugin_components"] = components
        except Exception as e:
            logger.error(f"Error setting plugin components: {e}")
        
        try:
            # Get plugin-specific dashboard actions (if any)
            plugin_actions = []
            for plugin_name, ui_provider in plugin_manager.get_all_plugin_uis().items():
                if hasattr(ui_provider, "get_dashboard_actions"):
                    try:
                        action = ui_provider.get_dashboard_actions(request)
                        if action:
                            plugin_actions.append(action)
                    except Exception as e:
                        logger.error(f"Error rendering dashboard actions for plugin {plugin_name}: {e}")
            context["plugin_actions"] = plugin_actions
        except Exception as e:
            logger.error(f"Error collecting plugin actions: {e}")
        
        return templates.TemplateResponse("dashboard.html", context)
        
    except Exception as e:
        logger.error(f"Critical error in dashboard route: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "An error occurred while loading the dashboard. Please try again or contact support.",
            "back_url": "/"
        })

@router.get("/graphql-playground", response_class=HTMLResponse)
async def graphql_playground_redirect(request: Request):
    """
    Redirects to the Twitter GraphQL playground provided by the Twitter GraphQL plugin.
    
    This route exists for backwards compatibility and redirects users to the new
    GraphQL playground route provided by the Twitter GraphQL plugin.
    """
    return RedirectResponse(url="/twitter/graphql/playground", status_code=301)