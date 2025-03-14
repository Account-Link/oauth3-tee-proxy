"""
Twitter Cookie Auth Routes
=========================

This module provides RESTful API endpoints for Twitter cookie authentication.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from plugins.twitter.models import TwitterAccount
from plugin_manager import plugin_manager

logger = logging.getLogger(__name__)


def create_cookie_auth_router() -> APIRouter:
    """
    Creates an API router for Twitter cookie authentication.
    
    Returns:
        APIRouter: FastAPI router with Twitter cookie auth routes
    """
    router = APIRouter(tags=["twitter:auth:cookies"])
    
    def handle_error(message: str, is_api_call: bool, status_code: int = 400) -> Response:
        """Helper function to handle errors consistently based on call type"""
        if is_api_call:
            raise HTTPException(status_code=status_code, detail=message)
        else:
            return RedirectResponse(
                url=f"/error?message={message}&back_url=/twitter/auth/admin", 
                status_code=303
            )
    
    async def extract_cookie(request: Request, twitter_cookie: str, cookie_data: dict) -> tuple:
        """Extract cookie from request and determine if it's an API call"""
        is_api_call = request.headers.get('content-type', '').startswith('application/json')
        cookie_string = None
        
        if is_api_call:
            # For JSON requests
            if cookie_data and 'cookie' in cookie_data:
                cookie_string = cookie_data['cookie']
                logger.debug("Found cookie in Body parameter")
            elif not cookie_data:
                try:
                    body = await request.json()
                    if 'cookie' in body:
                        cookie_string = body['cookie']
                        logger.debug("Found cookie in JSON body")
                except Exception as e:
                    logger.debug(f"Error parsing JSON body: {str(e)}")
        elif twitter_cookie:
            # For form submissions
            cookie_string = twitter_cookie
            is_api_call = False
            logger.debug("Found cookie in form data")
            
        return cookie_string, is_api_call
    
    async def update_or_create_account(db: Session, twitter_id: str, cookie_string: str, 
                               user_id: str, profile_info: dict) -> tuple:
        """Update existing account or create new one"""
        username = profile_info.get('username')
        display_name = profile_info.get('name')
        profile_image_url = profile_info.get('profile_image_url')
        
        existing_account = db.query(TwitterAccount).filter(
            TwitterAccount.twitter_id == twitter_id
        ).first()
        
        if existing_account:
            # Update existing account
            existing_account.twitter_cookie = cookie_string
            existing_account.updated_at = datetime.utcnow()
            existing_account.user_id = user_id
            
            # Update profile information if available
            if username:
                existing_account.username = username
            if display_name:
                existing_account.display_name = display_name
            if profile_image_url:
                existing_account.profile_image_url = profile_image_url
        else:
            # Create new account
            account = TwitterAccount(
                twitter_id=twitter_id,
                twitter_cookie=cookie_string,
                user_id=user_id,
                username=username,
                display_name=display_name,
                profile_image_url=profile_image_url
            )
            db.add(account)
            db.flush()  # Get the new ID
        
        db.commit()
        return username, display_name, profile_image_url
            
    @router.post("", status_code=201)
    async def create_cookie_auth(
        response: Response,
        db: Session = Depends(get_db),
        twitter_cookie: str = Form(None, description="Twitter cookie to submit"),
        request: Request = None,
        cookie_data: dict = Body(None)
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
            raise HTTPException(
                status_code=401, 
                detail="Authentication required. Please log in first."
            )
        
        try:
            # Extract cookie from request
            cookie_string, is_api_call = await extract_cookie(request, twitter_cookie, cookie_data)
            
            # Check if cookie was found
            if not cookie_string:
                return handle_error(
                    "No cookie provided. Please submit the cookie via form or API.",
                    is_api_call
                )
            
            # Get Twitter auth plugin
            twitter_auth = plugin_manager.create_authorization_plugin("twitter_cookie")
            if not twitter_auth:
                return handle_error(
                    "Twitter cookie authorization plugin not available",
                    is_api_call,
                    500
                )
            
            # Parse and validate the cookie
            try:
                credentials = twitter_auth.credentials_from_string(cookie_string)
            except ValueError as e:
                return handle_error(
                    f"Invalid Twitter cookie format: {str(e)}. Please provide the cookie in the format: auth_token=YOUR_COOKIE_VALUE",
                    is_api_call
                )
            
            # Validate credentials
            is_valid = await twitter_auth.validate_credentials(credentials)
            if not is_valid:
                return handle_error(
                    "Invalid Twitter cookie. The cookie may be expired or invalid. Please provide a fresh auth_token cookie from a logged-in Twitter session.",
                    is_api_call
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
                raise HTTPException(status_code=400, detail="Twitter account already linked to another user")
            
            # Basic validation - check if cookie is empty
            if not cookie_string:
                return handle_error("Cookie cannot be empty", is_api_call)
                
            # Update or create account
            username, display_name, profile_image_url = await update_or_create_account(
                db, twitter_id, cookie_string, request.session.get("user_id"), profile_info
            )
            
            logger.info(f"Successfully linked Twitter account {twitter_id} to user {request.session.get('user_id')}")
            
            # Return response based on call type
            if is_api_call:
                response.status_code = 201
                return {
                    "status": "success",
                    "message": "Twitter account successfully linked",
                    "account": {
                        "twitter_id": twitter_id,
                        "username": username,
                        "display_name": display_name,
                        "profile_image_url": profile_image_url
                    }
                }
            else:
                return RedirectResponse(url="/dashboard", status_code=303)
                
        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except ValueError as e:
            return handle_error(f"Invalid Twitter cookie: {str(e)}", is_api_call)
        except Exception as e:
            logger.error(f"Error processing cookie submission: {str(e)}", exc_info=True)
            return handle_error(
                f"An error occurred while processing your request: {str(e)}",
                is_api_call,
                500
            )
    
    return router