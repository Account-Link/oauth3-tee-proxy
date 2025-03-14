"""
Twitter Auth UI Routes
=====================

This module provides UI routes for Twitter authentication methods,
including cookie submission and OAuth-related user interfaces.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from plugin_manager import plugin_manager

logger = logging.getLogger(__name__)

def create_auth_ui_router() -> APIRouter:
    """
    Creates an API router for Twitter authentication UI routes.
    
    Returns:
        APIRouter: FastAPI router with Twitter auth UI routes
    """
    router = APIRouter(tags=["twitter:auth:ui"])
    
    @router.get("", response_class=HTMLResponse)
    async def twitter_auth_admin_page(request: Request, db: Session = Depends(get_db)):
        """
        Admin page for Twitter authentication options.
        Provides both cookie and OAuth authentication methods.
        """
        # Check if user is authenticated
        user_id = request.session.get("user_id")
        logger.debug(f"Session auth check for Twitter auth admin. Session user_id: {user_id}")
        
        # Also try to get user from JWT
        user_from_jwt = getattr(request.state, "user", None)
        logger.debug(f"JWT auth check for Twitter auth admin. JWT user: {user_from_jwt is not None}")
        
        if not user_id and not user_from_jwt:
            logger.warning("No authentication found, redirecting to login")
            return RedirectResponse(url="/auth/login")
            
        if not user_id and user_from_jwt:
            # Use JWT user if session is missing
            user_id = user_from_jwt.id
            logger.debug(f"Using JWT user_id: {user_id} instead of session")
        
        try:
            from fastapi.templating import Jinja2Templates
            
            # Get the Twitter UI provider from plugin manager
            twitter_ui = plugin_manager.get_plugin_ui("twitter")
            if twitter_ui and hasattr(twitter_ui, "render_auth_admin_page"):
                return twitter_ui.render_auth_admin_page(request)
            
            # Fallback to main templates
            template_dir = "plugins/twitter/templates"
            templates = Jinja2Templates(directory=template_dir)
            # Add the base templates directory
            templates.env.loader.searchpath.append("templates")
            
            # Check for existing Twitter accounts
            from plugins.twitter.models import TwitterAccount, TwitterOAuthCredential
            twitter_accounts = db.query(TwitterAccount).filter(
                TwitterAccount.user_id == user_id
            ).all()
            
            # Get OAuth credentials for existing accounts
            account_oauth_status = {}
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
        except Exception as e:
            logger.error(f"Error rendering Twitter auth admin page: {e}", exc_info=True)
            return RedirectResponse(
                url=f"/error?message=Error loading Twitter authentication options&back_url=/dashboard", 
                status_code=303
            )
    
    return router