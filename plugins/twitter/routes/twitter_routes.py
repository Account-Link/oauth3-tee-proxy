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
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from plugins.twitter.models import TwitterAccount, TweetLog
from oauth2_routes import OAuth2Token, verify_token_and_scopes
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
        
        @router.post("/cookie")
        async def submit_cookie(
            response: Response,
            db: Session = Depends(get_db),
            twitter_cookie: str = Form(...),
            request: Request = None
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
            
            try:
                # Get the Twitter auth plugin from our plugin manager
                from plugin_manager import plugin_manager
                twitter_auth = plugin_manager.create_authorization_plugin("twitter_cookie")
                if not twitter_auth:
                    raise HTTPException(
                        status_code=500,
                        detail="Twitter cookie authorization plugin not available"
                    )
                
                # Parse and validate the cookie
                credentials = twitter_auth.credentials_from_string(twitter_cookie)
                if not await twitter_auth.validate_credentials(credentials):
                    raise HTTPException(
                        status_code=400, 
                        detail="Invalid Twitter cookie. Please provide a valid cookie."
                    )
                
                # Get Twitter ID from the cookie
                twitter_id = await twitter_auth.get_user_identifier(credentials)
                
                # Check if account already exists
                existing_account = db.query(TwitterAccount).filter(
                    TwitterAccount.twitter_id == twitter_id
                ).first()
                
                if existing_account:
                    if existing_account.user_id and existing_account.user_id != request.session.get("user_id"):
                        raise HTTPException(status_code=400, detail="Twitter account already linked to another user")
                    existing_account.twitter_cookie = twitter_cookie
                    existing_account.updated_at = datetime.utcnow()
                    existing_account.user_id = request.session.get("user_id")
                else:
                    account = TwitterAccount(
                        twitter_id=twitter_id,
                        twitter_cookie=twitter_cookie,
                        user_id=request.session.get("user_id")
                    )
                    db.add(account)
                
                db.commit()
                logger.info(f"Successfully linked Twitter account {twitter_id} to user {request.session.get('user_id')}")
                return {"status": "success", "message": "Twitter account linked successfully"}
            except Exception as e:
                logger.error(f"Error processing cookie submission: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500, 
                    detail="An unexpected error occurred while processing your request."
                )
        
        @router.post("/tweet")
        async def post_tweet(
            tweet_data: TweetRequest,
            token: OAuth2Token = Security(verify_token_and_scopes, scopes=["tweet.post"]),
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
                
        return router