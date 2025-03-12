"""
Twitter Route Definitions
=======================

This module implements the FastAPI routes for Twitter functionality in the
OAuth3 TEE Proxy. It defines the HTTP endpoints that clients can use to
interact with Twitter via the proxy.

The TwitterRoutes class implements the RoutePlugin interface and provides
routes for:
- Twitter API interactions
- Policy management

This module no longer contains authentication or account management routes,
which have been moved to more specialized modules.
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
    TwitterOperationsPolicy, TwitterOperationSpec, TwitterOperationCategory,
    PolicyViolationError
)

# Import the new route modules
from .auth import create_auth_ui_router, create_cookie_auth_router
from .account_routes import create_account_router

logger = logging.getLogger(__name__)

class TweetRequest(BaseModel):
    """Request model for posting a tweet."""
    text: str
    reply_to_tweet_id: Optional[str] = None
    quote_tweet_id: Optional[str] = None

class TwitterRoutes(RoutePlugin):
    """
    Twitter route plugin that provides endpoints for interacting with Twitter.
    
    This plugin implements the RoutePlugin interface and registers routes for
    Twitter-specific functionality, including:
    - Twitter API interactions (tweets, etc.)
    - Policy management
    """
    
    service_name = "twitter"
    
    def create_routes(self) -> APIRouter:
        """
        Create and return an API router with Twitter routes.
        
        This method sets up all the HTTP endpoints for Twitter functionality
        and returns them as a FastAPI APIRouter that can be included in the
        main app.
        
        Returns:
            APIRouter: FastAPI router with Twitter-specific routes
        """
        router = APIRouter(tags=["twitter"])
        
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
                
                # Get the Twitter resource plugin
                from plugin_manager import plugin_manager
                twitter_resource = plugin_manager.create_resource_plugin(
                    "twitter", twitter_account.twitter_cookie)
                
                if not twitter_resource:
                    logger.error("Twitter resource plugin not available")
                    raise HTTPException(
                        status_code=500,
                        detail="Twitter API not available"
                    )
                
                # Filter tweet text for safety
                settings = get_twitter_settings()
                safety_filter = SafetyFilter.get_instance(settings.safety_level)
                filtered_text = safety_filter.filter_text(tweet_data.text)
                
                if filtered_text != tweet_data.text:
                    logger.warning(f"Tweet text was filtered for safety: {tweet_data.text} -> {filtered_text}")
                
                # Check policy for the operation
                try:
                    # Get the policy instance
                    policy = TwitterOperationsPolicy.get_instance()
                    
                    # Create operation spec for policy checking
                    operation_spec = TwitterOperationSpec(
                        category=TwitterOperationCategory.TWEET,
                        parameters={
                            "text": filtered_text,
                            "reply_to_tweet_id": tweet_data.reply_to_tweet_id,
                            "quote_tweet_id": tweet_data.quote_tweet_id
                        }
                    )
                    
                    # Check if operation is allowed
                    policy.check_operation(operation_spec)
                    
                except PolicyViolationError as e:
                    logger.warning(f"Policy violation when posting tweet: {str(e)}")
                    raise HTTPException(status_code=403, detail=f"Policy violation: {str(e)}")
                
                # Post the tweet
                tweet_id = await twitter_resource.post_tweet(
                    filtered_text,
                    reply_to_tweet_id=tweet_data.reply_to_tweet_id,
                    quote_tweet_id=tweet_data.quote_tweet_id
                )
                
                # Log the tweet
                tweet_log = TweetLog(
                    tweet_id=tweet_id,
                    user_id=token.user_id,
                    twitter_account_id=twitter_account.twitter_id,
                    content=filtered_text,
                    created_at=datetime.utcnow()
                )
                db.add(tweet_log)
                db.commit()
                
                return {
                    "tweet_id": tweet_id,
                    "text": filtered_text
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error posting tweet: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error posting tweet: {str(e)}")
        
        @router.get("/policy")
        async def get_policy(
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["twitter.policy.read"])
        ):
            """Get the current Twitter operations policy settings"""
            try:
                policy = TwitterOperationsPolicy.get_instance()
                return policy.get_policy()
            except Exception as e:
                logger.error(f"Error getting policy: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error getting policy: {str(e)}")
        
        @router.put("/policy")
        async def update_policy(
            policy_data: Dict[str, Any],
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["twitter.policy.write"])
        ):
            """Update the Twitter operations policy"""
            try:
                policy = TwitterOperationsPolicy.get_instance()
                policy.update_policy(policy_data)
                return {"status": "success", "message": "Policy updated"}
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"Error updating policy: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error updating policy: {str(e)}")
        
        @router.get("/policy/operations")
        async def get_policy_operations(
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["twitter.policy.read"])
        ):
            """Get all available Twitter operations that can be configured in the policy"""
            try:
                operations = TwitterOperationCategory.get_all_operations()
                return operations
            except Exception as e:
                logger.error(f"Error getting operations: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error getting operations: {str(e)}")
        
        @router.get("/policy/templates/{template_name}")
        async def get_policy_template(
            template_name: str,
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["twitter.policy.read"])
        ):
            """Get a predefined policy template by name"""
            try:
                policy = TwitterOperationsPolicy.get_instance()
                template = policy.get_template(template_name)
                if template:
                    return template
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Template '{template_name}' not found"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting policy template: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error getting policy template: {str(e)}"
                )
        
        # Include the auth routes with appropriate prefixes
        auth_ui_router = create_auth_ui_router()
        router.include_router(auth_ui_router, prefix="/auth/ui")
        
        cookie_auth_router = create_cookie_auth_router()
        router.include_router(cookie_auth_router, prefix="/auth/cookies")
        
        # Include the account routes with appropriate prefix
        account_router = create_account_router()
        router.include_router(account_router, prefix="/accounts")
        
        return router