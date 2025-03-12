"""
Twitter Cookie Auth Routes
=========================

This module provides RESTful API endpoints for Twitter cookie authentication.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Body, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from plugins.twitter.models import TwitterAccount

logger = logging.getLogger(__name__)

def create_cookie_auth_router() -> APIRouter:
    """
    Creates an API router for Twitter cookie authentication.
    
    Returns:
        APIRouter: FastAPI router with Twitter cookie auth routes
    """
    router = APIRouter(tags=["twitter:auth:cookies"])
    
    @router.post("", status_code=201)
    async def create_cookie_auth(
        response: Response,
        db: Session = Depends(get_db),
        twitter_cookie: str = Form(None, description="Twitter cookie to submit"),
        request: Request = None,
        cookie_data: dict = Body(None)
    ):
        # Debug the raw request body
        body_bytes = await request.body()
        logger.info(f"Raw request body: {body_bytes}")
        try:
            body_text = body_bytes.decode('utf-8')
            logger.info(f"Request body as text: {body_text}")
        except:
            logger.info("Could not decode request body as text")
        """
        Submit and validate a Twitter cookie.
        Links the Twitter account to the authenticated user.
        
        Returns:
            201: Twitter account successfully linked
            400: Invalid cookie
            401: Authentication required
        """
        if not request.session.get("user_id"):
            raise HTTPException(
                status_code=401, 
                detail="Authentication required. Please log in first."
            )
        
        # Debug the incoming request
        logger.info(f"Cookie submission - content type: {request.headers.get('content-type')}")
        logger.info(f"Form data present: {twitter_cookie is not None}")
        logger.info(f"JSON data present: {cookie_data is not None}")
        if cookie_data:
            logger.info(f"Cookie data keys: {cookie_data.keys() if hasattr(cookie_data, 'keys') else 'No keys method'}")
        
        # Support both form submission and JSON API
        cookie_string = None
        is_api_call = False
        
        try:
            # Check request content type to determine API call
            if request.headers.get('content-type', '').startswith('application/json'):
                is_api_call = True
                
                # For JSON requests, get the body
                if not cookie_data:
                    body = await request.json()
                    logger.info(f"Parsed request body: {body}")
                    if 'cookie' in body:
                        cookie_string = body['cookie']
                        logger.info("Found cookie in JSON body")
                else:
                    # Use cookie_data from the Body parameter
                    if 'cookie' in cookie_data:
                        cookie_string = cookie_data['cookie']
                        logger.info("Found cookie in Body parameter")
                    else:
                        logger.warning(f"Cookie not found in Body parameter. Keys: {cookie_data.keys() if hasattr(cookie_data, 'keys') else 'unknown'}")
            
            # For form submissions
            elif twitter_cookie:
                cookie_string = twitter_cookie
                is_api_call = False
                logger.info("Found cookie in form data")
            
            # If no cookie found anywhere
            if not cookie_string:
                error_message = "No cookie provided. Please submit the cookie via form or API."
                logger.warning(f"No cookie found in request. API call: {is_api_call}")
                
                if is_api_call:
                    raise HTTPException(status_code=400, detail=error_message)
                else:
                    return RedirectResponse(
                        url=f"/error?message={error_message}&back_url=/twitter/auth/admin", 
                        status_code=303
                    )
        except Exception as e:
            error_message = f"Error processing request: {str(e)}"
            logger.error(f"Error processing cookie request: {str(e)}", exc_info=True)
            
            if is_api_call:
                raise HTTPException(status_code=400, detail=error_message)
            else:
                return RedirectResponse(
                    url=f"/error?message={error_message}&back_url=/twitter/auth/admin", 
                    status_code=303
                )
        
        try:
            # Get the Twitter auth plugin from our plugin manager
            from plugin_manager import plugin_manager
            twitter_auth = plugin_manager.create_authorization_plugin("twitter_cookie")
            if not twitter_auth:
                error = "Twitter cookie authorization plugin not available"
                if is_api_call:
                    raise HTTPException(status_code=500, detail=error)
                else:
                    return RedirectResponse(
                        url=f"/error?message={error}&back_url=/twitter/auth/admin", 
                        status_code=303
                    )
            
            # Parse the cookie - log the first 10 characters for debugging
            logger.info(f"Processing cookie submission, cookie starts with: {cookie_string[:10]}...")
            
            # Parse and validate the cookie
            try:
                credentials = twitter_auth.credentials_from_string(cookie_string)
            except ValueError as e:
                error_message = f"Invalid Twitter cookie format: {str(e)}. Please provide the cookie in the format: auth_token=YOUR_COOKIE_VALUE"
                logger.error(f"Error parsing cookie: {str(e)}")
                
                if is_api_call:
                    raise HTTPException(status_code=400, detail=error_message)
                else:
                    return RedirectResponse(
                        url=f"/error?message={error_message}&back_url=/twitter/auth/admin", 
                        status_code=303
                    )
            
            # Validate credentials
            is_valid = await twitter_auth.validate_credentials(credentials)
            if not is_valid:
                error_message = "Invalid Twitter cookie. The cookie may be expired or invalid. Please provide a fresh auth_token cookie from a logged-in Twitter session."
                logger.error("Credentials validation failed")
                
                if is_api_call:
                    raise HTTPException(status_code=400, detail=error_message)
                else:
                    return RedirectResponse(
                        url=f"/error?message={error_message}&back_url=/twitter/auth/admin", 
                        status_code=303
                    )
            
            # Get Twitter ID and profile information from the cookie
            try:
                # Get basic user ID
                twitter_id = await twitter_auth.get_user_identifier(credentials)
                
                # Get additional profile information if available
                profile_info = await twitter_auth.get_user_profile(credentials)
                
                logger.info(f"Retrieved Twitter profile info: {profile_info}")
                username = profile_info.get('username')
                display_name = profile_info.get('name')
                profile_image_url = profile_info.get('profile_image_url')
                
            except ValueError as e:
                error_message = f"Could not get Twitter ID: {str(e)}"
                logger.error(f"Error getting Twitter ID: {str(e)}")
                
                if is_api_call:
                    raise HTTPException(status_code=400, detail=error_message)
                else:
                    return RedirectResponse(
                        url=f"/error?message={error_message}&back_url=/twitter/auth/admin", 
                        status_code=303
                    )
            
            # Check if account already exists
            existing_account = db.query(TwitterAccount).filter(
                TwitterAccount.twitter_id == twitter_id
            ).first()
            
            if existing_account:
                if existing_account.user_id and existing_account.user_id != request.session.get("user_id"):
                    raise HTTPException(status_code=400, detail="Twitter account already linked to another user")
                
                # Update existing account with fresh info
                # Just log the info and continue
                logger.info(f"Cookie value: '{twitter_cookie}'")
                logger.info(f"Cookie format: Length={len(twitter_cookie) if twitter_cookie else 0}, Type={type(twitter_cookie)}")
                if twitter_cookie:
                    logger.info(f"Cookie starts with: {twitter_cookie[:20]}...")
                    logger.info(f"Contains 'auth_token=': {'auth_token=' in twitter_cookie}")
                
                # Basic validation - only check if it's completely empty
                if not twitter_cookie:
                    error_message = "Cookie cannot be empty"
                    logger.error(error_message)
                    if is_api_call:
                        raise HTTPException(status_code=400, detail=error_message)
                    else:
                        return RedirectResponse(
                            url=f"/error?message={error_message}&back_url=/twitter/auth/admin", 
                            status_code=303
                        )
                        
                # Store the cookie directly in SQLite for consistency
                import sqlite3
                db_conn = sqlite3.connect('oauth3.db')
                cursor = db_conn.cursor()
                cursor.execute('UPDATE twitter_accounts SET twitter_cookie = ? WHERE twitter_id = ?', 
                               (twitter_cookie, existing_account.twitter_id))
                db_conn.commit()
                db_conn.close()
                
                # Also update via SQLAlchemy
                existing_account.twitter_cookie = twitter_cookie
                existing_account.updated_at = datetime.utcnow()
                existing_account.user_id = request.session.get("user_id")
                
                # Update profile information if available
                if username:
                    existing_account.username = username
                if display_name:
                    existing_account.display_name = display_name
                if profile_image_url:
                    existing_account.profile_image_url = profile_image_url
            else:
                # Just log the info and continue
                logger.info(f"New account - Cookie value: '{twitter_cookie}'")
                logger.info(f"New account - Cookie format: Length={len(twitter_cookie) if twitter_cookie else 0}, Type={type(twitter_cookie)}")
                if twitter_cookie:
                    logger.info(f"New account - Cookie starts with: {twitter_cookie[:20]}...")
                    logger.info(f"New account - Contains 'auth_token=': {'auth_token=' in twitter_cookie}")
                
                # Basic validation - only check if it's completely empty
                if not twitter_cookie:
                    error_message = "Cookie cannot be empty"
                    logger.error(error_message)
                    if is_api_call:
                        raise HTTPException(status_code=400, detail=error_message)
                    else:
                        return RedirectResponse(
                            url=f"/error?message={error_message}&back_url=/twitter/auth/admin", 
                            status_code=303
                        )
                        
                # Create new account with all available info
                account = TwitterAccount(
                    twitter_id=twitter_id,
                    twitter_cookie=twitter_cookie,
                    user_id=request.session.get("user_id"),
                    username=username,
                    display_name=display_name,
                    profile_image_url=profile_image_url
                )
                db.add(account)
                
                # Also store directly in SQLite for consistency
                db.flush()  # Get the new ID
                import sqlite3
                db_conn = sqlite3.connect('oauth3.db')
                cursor = db_conn.cursor()
                cursor.execute('UPDATE twitter_accounts SET twitter_cookie = ? WHERE twitter_id = ?', 
                               (twitter_cookie, twitter_id))
                db_conn.commit()
                db_conn.close()
            
            db.commit()
            logger.info(f"Successfully linked Twitter account {twitter_id} to user {request.session.get('user_id')}")
            
            # Return different response based on call type
            if is_api_call:
                # Set response status for API calls
                response.status_code = 201
                # Return account info for API calls
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
                # Return a redirect for form submissions
                return RedirectResponse(url="/dashboard", status_code=303)
                
        except HTTPException:
            # Re-raise HTTP exceptions directly to preserve their status code and detail
            raise
        except ValueError as e:
            # Handle ValueError separately with a 400 status code
            error_message = f"Invalid Twitter cookie: {str(e)}"
            logger.error(f"Value error processing cookie: {str(e)}", exc_info=True)
            
            if is_api_call:
                raise HTTPException(status_code=400, detail=error_message)
            else:
                # Redirect to error page for form submissions
                return RedirectResponse(
                    url=f"/error?message={error_message}&back_url=/twitter/auth/admin", 
                    status_code=303
                )
        except Exception as e:
            # Log any other unexpected errors
            error_message = f"An error occurred while processing your request: {str(e)}"
            logger.error(f"Error processing cookie submission: {str(e)}", exc_info=True)
            
            if is_api_call:
                raise HTTPException(status_code=500, detail=error_message)
            else:
                # Redirect to error page for form submissions
                return RedirectResponse(
                    url=f"/error?message={error_message}&back_url=/twitter/auth/admin", 
                    status_code=303
                )
    
    return router