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
    # Get the Twitter UI provider and render the submit cookie page
    twitter_ui = plugin_manager.get_plugin_ui("twitter")
    if twitter_ui and hasattr(twitter_ui, "render_submit_cookie_page"):
        return twitter_ui.render_submit_cookie_page(request)
    
    # Fallback to the old template if the UI provider is not available
    return templates.TemplateResponse("submit_cookie.html", {"request": request})

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
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    # Get accounts from enabled plugins
    twitter_accounts = []
    telegram_accounts = []
    
    # Check if Twitter plugin is available
    if any(plugin.service_name == "twitter" for plugin in plugin_manager.get_all_resource_plugins().values()):
        twitter_accounts = db.query(TwitterAccount).filter(
            TwitterAccount.user_id == user_id
        ).all()
    
    # Check if Telegram plugin is available
    if any(plugin.service_name == "telegram" for plugin in plugin_manager.get_all_resource_plugins().values()):
        telegram_accounts = db.query(TelegramAccount).filter(
            TelegramAccount.user_id == user_id
        ).all()
        
        # Get channels for each Telegram account
        for account in telegram_accounts:
            account.channels = db.query(TelegramChannel).filter(
                TelegramChannel.telegram_account_id == account.id
            ).all()
    
    # Get active OAuth2 tokens
    oauth2_tokens = db.query(OAuth2Token).filter(
        OAuth2Token.user_id == user_id,
        OAuth2Token.is_active == True,
        OAuth2Token.expires_at > datetime.utcnow()
    ).all()
    
    # Get all available scopes from plugins
    available_scopes = plugin_manager.get_all_plugin_scopes()
    
    # Create the template context
    context = {
        "request": request,
        "user": user,
        "twitter_accounts": twitter_accounts,
        "telegram_accounts": telegram_accounts,
        "oauth2_tokens": oauth2_tokens,
        "available_scopes": available_scopes.keys()
    }
    
    # Render plugin-specific UI components
    context["plugin_components"] = plugin_manager.render_dashboard_components(request, context)
    
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
    
    return templates.TemplateResponse("dashboard.html", context)

@router.get("/graphql-playground", response_class=HTMLResponse)
async def graphql_playground(request: Request, db: Session = Depends(get_db)):
    """
    Twitter GraphQL API playground for testing queries.
    
    This page provides a user interface for testing Twitter GraphQL queries through
    the OAuth3 TEE Proxy. It allows selecting from predefined operations or entering
    custom query IDs, and supports both GET and POST methods.
    
    This route now uses the Twitter plugin's UI provider to render the template.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    # Get active OAuth2 tokens with appropriate scopes
    oauth2_tokens = db.query(OAuth2Token).filter(
        OAuth2Token.user_id == user_id,
        OAuth2Token.is_active == True,
        OAuth2Token.expires_at > datetime.utcnow(),
        OAuth2Token.scopes.contains("twitter.graphql")
    ).all()
    
    # Import the Twitter GraphQL operations - use a lazy import to avoid circular dependencies
    from plugins.twitter.policy import TWITTER_GRAPHQL_OPERATIONS
    
    # Get the Twitter UI provider and render the GraphQL playground
    twitter_ui = plugin_manager.get_plugin_ui("twitter")
    if twitter_ui and hasattr(twitter_ui, "render_graphql_playground"):
        return twitter_ui.render_graphql_playground(request, oauth2_tokens, TWITTER_GRAPHQL_OPERATIONS)
    
    # Fallback to the old template if the UI provider is not available
    return templates.TemplateResponse(
        "graphql_playground.html",
        {
            "request": request,
            "user": user,
            "oauth2_tokens": oauth2_tokens,
            "operations": TWITTER_GRAPHQL_OPERATIONS
        }
    )