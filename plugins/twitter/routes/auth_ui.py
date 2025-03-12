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
    async def submit_cookie_page(request: Request):
        """
        Page for submitting Twitter cookie authentication.
        """
        # Check if user is authenticated
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login")
        
        try:
            from fastapi.templating import Jinja2Templates
            
            # Get the Twitter UI provider from plugin manager
            twitter_ui = plugin_manager.get_plugin_ui("twitter")
            if twitter_ui and hasattr(twitter_ui, "render_submit_cookie_page"):
                return twitter_ui.render_submit_cookie_page(request)
            
            # Fallback to main templates
            templates = Jinja2Templates(directory="templates")
            return templates.TemplateResponse("submit_cookie.html", {"request": request})
        except Exception as e:
            logger.error(f"Error rendering submit_cookie page: {e}")
            return RedirectResponse(
                url=f"/error?message=Error loading Twitter cookie form&back_url=/dashboard", 
                status_code=303
            )
    
    return router