"""
Twitter Cookie Auth Routes
=========================

This module provides RESTful API endpoints for Twitter cookie authentication.
Only accepts JSON requests and always responds with JSON.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from plugins.twitter.models import TwitterAccount
from plugin_manager import plugin_manager

logger = logging.getLogger(__name__)


class CookieRequest(BaseModel):
    """Model for Twitter cookie submission request"""
    cookie: str


def create_cookie_auth_router() -> APIRouter:
    """
    Creates an API router for Twitter cookie authentication.
    
    Returns:
        APIRouter: FastAPI router with Twitter cookie auth routes
    """
    router = APIRouter(tags=["twitter:auth:cookies"])
    
    def handle_error(message: str, status_code: int = 400) -> JSONResponse:
        """Helper function to handle errors consistently"""
        return JSONResponse(
            status_code=status_code,
            content={"status": "error", "message": message}
        )
    
    async def extract_cookie(cookie_data: CookieRequest) -> str:
        """Extract cookie from request data"""
        if not cookie_data or not cookie_data.cookie:
            return None
        return cookie_data.cookie
    
            
    @router.post("", status_code=status.HTTP_201_CREATED, response_class=JSONResponse)
    async def create_cookie_auth(
        request: Request,
        cookie_data: CookieRequest,
        db: Session = Depends(get_db)
    ):
        """
        Submit and validate a Twitter cookie.
        Links the Twitter account to the authenticated user.
        
        Returns:
            201: Twitter account successfully linked
            400: Invalid cookie
            401: Authentication required
        """
        # Check authentication
        if not request.session.get("user_id"):
            return handle_error(
                "Authentication required. Please log in first.",
                status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            # Extract cookie from request
            cookie_string = await extract_cookie(cookie_data)
            
            # Check if cookie was found
            if not cookie_string:
                return handle_error(
                    "No cookie provided. Please submit the cookie in the request body.",
                    status.HTTP_400_BAD_REQUEST
                )
            
            # Get Twitter auth plugin
            twitter_auth = plugin_manager.create_authorization_plugin("twitter_cookie")
            if not twitter_auth:
                return handle_error(
                    "Twitter cookie authorization plugin not available",
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Parse and validate the cookie
            try:
                credentials = twitter_auth.credentials_from_string(cookie_string)
            except ValueError as e:
                return handle_error(
                    f"Invalid Twitter cookie format: {str(e)}. Please provide the cookie in the format: auth_token=YOUR_COOKIE_VALUE",
                    status.HTTP_400_BAD_REQUEST
                )
            
            # Validate credentials
            is_valid = await twitter_auth.validate_credentials(credentials)
            if not is_valid:
                return handle_error(
                    "Invalid Twitter cookie. The cookie may be expired or invalid. Please provide a fresh auth_token cookie from a logged-in Twitter session.",
                    status.HTTP_400_BAD_REQUEST
                )
            
            # Get Twitter ID and profile
            twitter_id = await twitter_auth.get_user_identifier(credentials)
            profile_info = await twitter_auth.get_user_profile(credentials)
            logger.debug(f"Retrieved Twitter profile info: {profile_info}")
            
            # Check if account exists and is linked to another user
            existing_account = db.query(TwitterAccount).filter(
                TwitterAccount.twitter_id == twitter_id
            ).first()
            
            if existing_account and existing_account.user_id and existing_account.user_id != request.session.get("user_id"):
                return handle_error(
                    "Twitter account already linked to another user",
                    status.HTTP_400_BAD_REQUEST
                )
            
            # Basic validation - check if cookie is empty
            if not cookie_string:
                return handle_error(
                    "Cookie cannot be empty",
                    status.HTTP_400_BAD_REQUEST
                )
                
            # Update or create account
            username, display_name, profile_image_url = await twitter_auth.update_or_create_account(
                db, twitter_id, cookie_string, request.session.get("user_id"), profile_info
            )
            
            logger.info(f"Successfully linked Twitter account {twitter_id} to user {request.session.get('user_id')}")
            
            # Return successful JSON response
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status": "success",
                    "message": "Twitter account successfully linked",
                    "account": {
                        "twitter_id": twitter_id,
                        "username": username,
                        "display_name": display_name,
                        "profile_image_url": profile_image_url
                    }
                }
            )
                
        except ValueError as e:
            return handle_error(
                f"Invalid Twitter cookie: {str(e)}",
                status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error processing cookie submission: {str(e)}", exc_info=True)
            return handle_error(
                f"An error occurred while processing your request: {str(e)}",
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return router