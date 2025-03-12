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
                            "GraphQL Playground": "/twitter/graphql/playground",
                            "Add Account": "/twitter/submit-cookie"
                        }
                    }
                
                if any(plugin.service_name == "telegram" for plugin in plugin_manager.get_all_resource_plugins().values()):
                    context["available_plugins"]["telegram"] = {
                        "name": "telegram",
                        "description": "Access Telegram channels and messages through OAuth3 TEE Proxy.",
                        "urls": {
                            "Add Account": "/telegram/add-account"
                        }
                    }
        except Exception as e:
            logger.error(f"Error in plugin info fallback: {e}")
        
        try:
            # Render plugin-specific UI components
            components = []
            try:
                components = plugin_manager.render_dashboard_components(request, context)
                # Debug logging for components
                for i, comp in enumerate(components):
                    logger.info(f"Dashboard component {i+1} type: {type(comp)}")
                    logger.info(f"Dashboard component {i+1} length: {len(comp) if comp else 0}")
                    # Check if it contains Twitter account IDs
                    for acct in context["twitter_accounts"]:
                        if comp and acct.twitter_id in comp:
                            logger.info(f"Component {i+1} contains Twitter account {acct.twitter_id}")
                        else:
                            logger.warning(f"Component {i+1} does NOT contain Twitter account {acct.twitter_id}")
            except Exception as e:
                logger.error(f"Error rendering plugin components: {e}")
            
            # Save components to context
            logger.info(f"Setting plugin_components in context with {len(components)} components")
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

