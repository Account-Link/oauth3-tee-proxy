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
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Security, Form, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from plugins.twitter.models import TwitterAccount, TweetLog
from oauth2_routes import OAuth2Token, verify_token_and_scopes
from safety import SafetyFilter, SafetyLevel
from plugins.twitter.config import get_twitter_settings
from plugins import RoutePlugin

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
                
        return router