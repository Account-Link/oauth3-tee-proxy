# plugins/twitter/routes/twitter_routes.py
"""
Twitter Route Definitions
=======================

This module implements the FastAPI routes for Twitter functionality in the
OAuth3 TEE Proxy. It defines the HTTP endpoints that clients can use to
interact with Twitter via the proxy.

The TwitterRoutes class implements the RoutePlugin interface and provides
routes for:
- Linking Twitter accounts (via cookie authentication)
- Posting tweets

The routes work with authorization and resource plugins to authenticate
users and access Twitter resources, but they themselves are only responsible
for HTTP interface aspects.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Security, Form, Response, Body, Query, Path
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from plugins.twitter.models import TwitterAccount, TweetLog
from models import OAuth2Token

# Lazily import verify_token_and_scopes to avoid circular imports
def get_verify_token_function():
    from oauth2_routes import verify_token_and_scopes
    return verify_token_and_scopes
from safety import SafetyFilter, SafetyLevel
from plugins.twitter.config import get_twitter_settings
from plugins import RoutePlugin
from plugins.twitter.policy import (
    TwitterPolicy, 
    TWITTER_GRAPHQL_OPERATIONS,
    get_read_operations,
    get_write_operations
)

logger = logging.getLogger(__name__)
settings = get_twitter_settings()

# Pydantic models for request validation
class TwitterCookieSubmit(BaseModel):
    """Model for submitting Twitter cookie."""
    twitter_cookie: str

class TweetRequest(BaseModel):
    """Model for tweet requests."""
    text: str
    bypass_safety: bool = False

class TwitterRoutes(RoutePlugin):
    """
    Plugin for Twitter API routes.
    
    This class implements the RoutePlugin interface for Twitter routes,
    providing HTTP endpoints for Twitter functionality in the OAuth3 TEE Proxy.
    The routes handle HTTP aspects of Twitter operations, delegating actual
    authentication and resource access to the appropriate plugins.
    
    The routes are mounted under the "/twitter" prefix in the main application.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin ("twitter")
    """
    
    service_name = "twitter"
    
    def get_router(self) -> APIRouter:
        """
        Get the router for Twitter-specific routes.
        
        Implements the RoutePlugin interface to provide Twitter-specific routes.
        The routes handle Twitter cookie submission, posting tweets, and other
        Twitter-specific operations.
        
        Returns:
            APIRouter: FastAPI router with Twitter-specific routes
        """
        router = APIRouter(tags=["twitter"])
        
        @router.get("/submit-cookie", response_class=HTMLResponse)
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
                import os
                
                # Use the main template renderer instead of the plugin's
                from plugin_manager import plugin_manager
                
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
        
        @router.post("/cookie")
        async def submit_cookie(
            response: Response,
            db: Session = Depends(get_db),
            twitter_cookie: str = Form(None, description="Twitter cookie to submit"),
            request: Request = None,
            cookie_data: dict = Body(None)
        ):
            """
            Submit and validate a Twitter cookie.
            Links the Twitter account to the authenticated user.
            """
            if not request.session.get("user_id"):
                raise HTTPException(
                    status_code=401, 
                    detail="Authentication required. Please log in first."
                )
            
            # Support both form submission and JSON API
            cookie_string = None
            
            # Check if this is a form submission or API call
            if twitter_cookie:
                cookie_string = twitter_cookie
                is_api_call = False
            elif cookie_data and 'cookie' in cookie_data:
                cookie_string = cookie_data['cookie']
                is_api_call = True
            else:
                # Neither form nor API provided the cookie
                error_message = "No cookie provided. Please submit the cookie via form or API."
                if request.headers.get('content-type') == 'application/json':
                    # API call but no cookie
                    raise HTTPException(status_code=400, detail=error_message)
                else:
                    # Form submission but no cookie
                    return RedirectResponse(
                        url=f"/error?message={error_message}&back_url=/twitter/submit-cookie", 
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
                            url=f"/error?message={error}&back_url=/twitter/submit-cookie", 
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
                            url=f"/error?message={error_message}&back_url=/twitter/submit-cookie", 
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
                            url=f"/error?message={error_message}&back_url=/twitter/submit-cookie", 
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
                            url=f"/error?message={error_message}&back_url=/twitter/submit-cookie", 
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
                
                db.commit()
                logger.info(f"Successfully linked Twitter account {twitter_id} to user {request.session.get('user_id')}")
                
                # Return different response based on call type
                if is_api_call:
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
                        url=f"/error?message={error_message}&back_url=/twitter/submit-cookie", 
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
                        url=f"/error?message={error_message}&back_url=/twitter/submit-cookie", 
                        status_code=303
                    )
        
        @router.post("/tweet")
        async def post_tweet(
            tweet_data: TweetRequest,
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["tweet.post"]),
            db: Session = Depends(get_db)
        ):
            """Post a tweet using the authenticated user's Twitter account"""
            try:
                twitter_account = db.query(TwitterAccount).filter(
                    TwitterAccount.user_id == token.user_id
                ).first()
                
                if not twitter_account:
                    logger.error(f"No Twitter account found for user {token.user_id}")
                    raise HTTPException(status_code=404, detail="Twitter account not found")
                
                # Safety check
                # Get the main settings for core functionality
                from config import get_settings
                core_settings = get_settings()
                
                if core_settings.SAFETY_FILTER_ENABLED and settings.SAFETY_FILTER_ENABLED and not tweet_data.bypass_safety:
                    safety_filter = SafetyFilter(level=SafetyLevel.MODERATE)
                    is_safe, reason = await safety_filter.check_tweet(tweet_data.text)
                    
                    if not is_safe:
                        # Log failed tweet
                        tweet_log = TweetLog(
                            user_id=token.user_id,
                            tweet_text=tweet_data.text,
                            safety_check_result=False,
                            safety_check_message=reason
                        )
                        db.add(tweet_log)
                        db.commit()
                        logger.warning(f"Tweet failed safety check for user {token.user_id}: {reason}")
                        
                        raise HTTPException(status_code=400, detail=f"Tweet failed safety check: {reason}")
                
                # Get the authorization plugin to parse credentials and resource plugin to post the tweet
                from plugin_manager import plugin_manager
                twitter_auth = plugin_manager.create_authorization_plugin("twitter_cookie")
                twitter_resource = plugin_manager.create_resource_plugin("twitter")
                
                if not twitter_auth or not twitter_resource:
                    raise HTTPException(
                        status_code=500,
                        detail="Required Twitter plugins not available"
                    )
                
                # Get credentials and initialize client
                credentials = twitter_auth.credentials_from_string(twitter_account.twitter_cookie)
                client = await twitter_resource.initialize_client(credentials)
                
                # Post tweet
                tweet_id = await twitter_resource.post_tweet(client, tweet_data.text)
                
                # Log successful tweet
                tweet_log = TweetLog(
                    user_id=token.user_id,
                    tweet_text=tweet_data.text,
                    safety_check_result=True,
                    tweet_id=tweet_id
                )
                db.add(tweet_log)
                db.commit()
                logger.info(f"Successfully posted tweet {tweet_id} for user {token.user_id}")
                
                return {"status": "success", "tweet_id": tweet_id}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error posting tweet for user {token.user_id}: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal server error")
        
        # Add policy-related routes
        @router.get("/policy")
        async def get_policy(
            request: Request,
            db: Session = Depends(get_db)
        ):
            """
            Get the current policy for the authenticated user's Twitter account.
            
            This endpoint returns the policy configuration for the authenticated user's
            Twitter account, including the allowed operations and categories.
            
            Args:
                request (Request): The HTTP request object
                db (Session): The database session
                
            Returns:
                Dict[str, Any]: The policy configuration
            """
            # Check if user is authenticated via session
            user_id = request.session.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            # Get the Twitter account
            twitter_account = db.query(TwitterAccount).filter(
                TwitterAccount.user_id == user_id
            ).first()
            
            if not twitter_account:
                raise HTTPException(
                    status_code=404,
                    detail="Twitter account not found"
                )
            
            # Return the policy
            return twitter_account.policy
        
        @router.put("/policy")
        async def set_policy(
            policy: Dict[str, Any] = Body(...),
            request: Request = None,
            db: Session = Depends(get_db)
        ):
            """
            Set the policy for the authenticated user's Twitter account.
            
            This endpoint allows users to configure the policy for their Twitter account,
            specifying which operations are allowed.
            
            Args:
                policy (Dict[str, Any]): The policy configuration
                request (Request): The HTTP request object
                db (Session): The database session
                
            Returns:
                Dict[str, Any]: Status message
            """
            # Check if user is authenticated via session
            user_id = request.session.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            # Get the Twitter account
            twitter_account = db.query(TwitterAccount).filter(
                TwitterAccount.user_id == user_id
            ).first()
            
            if not twitter_account:
                raise HTTPException(
                    status_code=404,
                    detail="Twitter account not found"
                )
            
            # Validate the policy
            # Create a TwitterPolicy object to validate the policy
            try:
                twitter_policy = TwitterPolicy.from_dict(policy)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid policy configuration: {str(e)}"
                )
            
            # Set the policy
            twitter_account.policy = policy
            db.commit()
            
            return {"status": "success", "message": "Policy updated"}
        
        @router.get("/policy/operations")
        async def get_operations(
            category: Optional[str] = Query(None, description="Filter operations by category (read or write)")
        ):
            """
            Get the available operations for Twitter GraphQL API.
            
            This endpoint returns the available operations for the Twitter GraphQL API,
            optionally filtered by category.
            
            Args:
                category (Optional[str]): Filter operations by category (read or write)
                
            Returns:
                Dict[str, Any]: The available operations
            """
            if category == "read":
                operations = {
                    query_id: TWITTER_GRAPHQL_OPERATIONS[query_id]
                    for query_id in get_read_operations()
                }
            elif category == "write":
                operations = {
                    query_id: TWITTER_GRAPHQL_OPERATIONS[query_id]
                    for query_id in get_write_operations()
                }
            else:
                operations = TWITTER_GRAPHQL_OPERATIONS
            
            return operations
        
        @router.get("/policy/templates/{template_name}")
        async def get_policy_template(
            template_name: str = Path(..., description="The name of the template to get")
        ):
            """
            Get a policy template.
            
            This endpoint returns a predefined policy template that can be used
            as a starting point for configuring access policies.
            
            Args:
                template_name (str): The name of the template to get
                
            Returns:
                Dict[str, Any]: The policy template
            """
            if template_name == "default":
                return TwitterPolicy.get_default_policy().to_dict()
            elif template_name == "read_only":
                return TwitterPolicy.get_read_only_policy().to_dict()
            elif template_name == "write_only":
                return TwitterPolicy.get_write_only_policy().to_dict()
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Template '{template_name}' not found"
                )
        
        @router.delete("/accounts/{twitter_id}")
        async def delete_twitter_account(
            twitter_id: str,
            request: Request,
            db: Session = Depends(get_db)
        ):
            """
            Delete a Twitter account association.
            
            This endpoint removes the association between a user and a Twitter account,
            deleting the Twitter account record from the database.
            
            Args:
                twitter_id (str): The Twitter ID to delete
                request (Request): The FastAPI request object
                db (Session): Database session dependency
                
            Returns:
                Dict[str, Any]: Status message
            """
            # Check if user is authenticated via session
            user_id = request.session.get("user_id")
            if not user_id:
                return RedirectResponse(url="/login", status_code=303)
            
            try:
                # Get the Twitter account
                twitter_account = db.query(TwitterAccount).filter(
                    TwitterAccount.twitter_id == twitter_id,
                    TwitterAccount.user_id == user_id
                ).first()
                
                if not twitter_account:
                    error_message = "Twitter account not found or does not belong to you"
                    return RedirectResponse(
                        url=f"/error?message={error_message}&back_url=/dashboard",
                        status_code=303
                    )
                
                # Delete the account
                db.delete(twitter_account)
                db.commit()
                
                logger.info(f"Successfully deleted Twitter account {twitter_id} for user {user_id}")
                
                # Check if this is an API call based on Accept header
                if request.headers.get("accept") == "application/json":
                    return {
                        "status": "success",
                        "message": f"Successfully deleted Twitter account {twitter_id}",
                        "twitter_id": twitter_id
                    }
                else:
                    # Traditional web form flow
                    return RedirectResponse(url="/dashboard", status_code=303)
                
            except Exception as e:
                logger.error(f"Error deleting Twitter account: {str(e)}", exc_info=True)
                error_message = f"Error deleting Twitter account: {str(e)}"
                if request.headers.get("accept") == "application/json":
                    return JSONResponse(
                        status_code=500,
                        content={"status": "error", "detail": error_message}
                    )
                else:
                    return RedirectResponse(
                        url=f"/error?message={error_message}&back_url=/dashboard",
                        status_code=303
                    )
                
        @router.delete("/accounts")
        async def delete_all_twitter_accounts(
            request: Request,
            db: Session = Depends(get_db)
        ):
            """
            Delete all Twitter accounts associated with the current user.
            
            This endpoint removes all Twitter accounts linked to the current user's profile.
            This is a destructive action and cannot be undone.
            
            Args:
                request (Request): The FastAPI request object
                db (Session): Database session dependency
                
            Returns:
                RedirectResponse: Redirect to dashboard
            """
            # Check if user is authenticated via session
            user_id = request.session.get("user_id")
            if not user_id:
                return RedirectResponse(url="/login", status_code=303)
            
            try:
                # Get all Twitter accounts for this user
                deleted_count = db.query(TwitterAccount).filter(
                    TwitterAccount.user_id == user_id
                ).delete(synchronize_session=False)
                
                # Commit the deletion
                db.commit()
                
                logger.info(f"Successfully deleted {deleted_count} Twitter accounts for user {user_id}")
                
                # Check if this is an API call based on Accept header
                if request.headers.get("accept") == "application/json":
                    return {
                        "status": "success",
                        "message": f"Successfully deleted {deleted_count} Twitter accounts",
                        "count": deleted_count
                    }
                else:
                    # Traditional web form flow
                    return RedirectResponse(url="/dashboard", status_code=303)
                
            except Exception as e:
                logger.error(f"Error deleting all Twitter accounts: {str(e)}", exc_info=True)
                error_message = f"Error deleting all Twitter accounts: {str(e)}"
                if request.headers.get("accept") == "application/json":
                    return JSONResponse(
                        status_code=500,
                        content={"status": "error", "detail": error_message}
                    )
                else:
                    return RedirectResponse(
                        url=f"/error?message={error_message}&back_url=/dashboard",
                        status_code=303
                    )
        
                
        return router