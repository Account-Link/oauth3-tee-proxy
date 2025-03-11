# plugins/twitter/routes/oauth_routes.py
"""
Twitter OAuth Routes
==================

This module implements HTTP routes for Twitter OAuth functionality in the
OAuth3 TEE Proxy. It defines the HTTP endpoints that clients can use to
authenticate with Twitter using the OAuth 1.0a flow.

The TwitterOAuthRoutes class implements the RoutePlugin interface and provides
routes for:
- Initiating Twitter OAuth flow
- Processing OAuth callbacks
- Managing Twitter OAuth credentials
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Response, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User
from plugins.twitter.models import TwitterAccount, TwitterOAuthCredential
from plugins import RoutePlugin

logger = logging.getLogger(__name__)

class TwitterOAuthRoutes(RoutePlugin):
    """
    Plugin for Twitter OAuth routes.
    
    This class implements the RoutePlugin interface for Twitter OAuth routes,
    providing HTTP endpoints for authenticating with Twitter using the OAuth flow.
    
    The routes are mounted under the "/twitter/oauth" prefix in the application.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin
    """
    
    service_name = "twitter/oauth"
    
    def get_router(self) -> APIRouter:
        """
        Get the router for Twitter OAuth routes.
        
        Returns a FastAPI router with endpoints for Twitter OAuth authentication.
        
        Returns:
            APIRouter: FastAPI router with Twitter OAuth routes
        """
        router = APIRouter(prefix="/oauth", tags=["twitter", "oauth"])
        
        @router.get("/login")
        async def twitter_oauth_login(
            request: Request,
            next: str = Query(None),
            callback_url: str = Query(None)
        ):
            """
            Initiate Twitter OAuth login.
            
            This endpoint starts the Twitter OAuth flow, redirecting the user
            to Twitter's authorization page.
            
            Args:
                request (Request): The HTTP request object
                next (str, optional): URL to redirect to after successful authentication
                callback_url (str, optional): Custom callback URL for the OAuth flow
                
            Returns:
                RedirectResponse: Redirect to Twitter's authorization page
            """
            try:
                # Import Twitter OAuth plugin
                from plugin_manager import plugin_manager
                twitter_oauth = plugin_manager.create_authorization_plugin("twitter_oauth")
                
                if not twitter_oauth:
                    raise HTTPException(
                        status_code=500,
                        detail="Twitter OAuth plugin not available"
                    )
                
                # Get authorization URL and request token
                redirect_url, request_token = await twitter_oauth.get_authorization_url(callback_url)
                
                # Store request token and flow type in session
                request.session["twitter_request_token"] = request_token
                request.session["twitter_auth_flow"] = "login"  # This is a login flow
                
                # Store next URL if provided
                if next:
                    request.session["twitter_auth_next"] = next
                
                # Redirect to Twitter authorization page
                return RedirectResponse(redirect_url)
                
            except Exception as e:
                logger.error(f"Error initiating Twitter OAuth login: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Error initiating Twitter login"
                )
        
        @router.get("/callback")
        async def twitter_oauth_callback(
            request: Request,
            oauth_token: str = Query(None),
            oauth_verifier: str = Query(None),
            db: Session = Depends(get_db)
        ):
            """
            Handle Twitter OAuth callback.
            
            This endpoint processes the callback from Twitter after the user
            has authorized the application.
            
            Args:
                request (Request): The HTTP request object
                oauth_token (str): The OAuth token returned by Twitter
                oauth_verifier (str): The OAuth verifier returned by Twitter
                db (Session): The database session
                
            Returns:
                RedirectResponse: Redirect to the next URL or dashboard
            """
            if not oauth_token or not oauth_verifier:
                raise HTTPException(
                    status_code=400,
                    detail="Missing OAuth parameters"
                )
            
            # Get request token from session
            request_token = request.session.get("twitter_request_token")
            if not request_token:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid session state"
                )
            
            try:
                # Import Twitter OAuth plugin
                from plugin_manager import plugin_manager
                twitter_oauth = plugin_manager.create_authorization_plugin("twitter_oauth")
                
                if not twitter_oauth:
                    raise HTTPException(
                        status_code=500,
                        detail="Twitter OAuth plugin not available"
                    )
                
                # Process the callback
                credentials = await twitter_oauth.process_callback(request_token, oauth_verifier)
                
                # Get Twitter ID from credentials
                twitter_id = credentials["user_id"]
                
                # Get auth flow type and next URL from session
                auth_flow = request.session.get("twitter_auth_flow", "login")
                next_url = request.session.get("twitter_auth_next", "/dashboard")
                
                # Check if Twitter account exists
                twitter_account = db.query(TwitterAccount).filter(
                    TwitterAccount.twitter_id == twitter_id
                ).first()
                
                # Handle existing account
                if twitter_account:
                    if auth_flow == "login" and twitter_account.can_login:
                        # Set session for this user
                        request.session["user_id"] = twitter_account.user_id
                        
                        # Update or create OAuth credentials
                        oauth_cred = db.query(TwitterOAuthCredential).filter(
                            TwitterOAuthCredential.twitter_account_id == twitter_id
                        ).first()
                        
                        if oauth_cred:
                            oauth_cred.oauth_token = credentials["oauth_token"]
                            oauth_cred.oauth_token_secret = credentials["oauth_token_secret"]
                            oauth_cred.updated_at = datetime.utcnow()
                        else:
                            oauth_cred = TwitterOAuthCredential(
                                twitter_account_id=twitter_id,
                                oauth_token=credentials["oauth_token"],
                                oauth_token_secret=credentials["oauth_token_secret"]
                            )
                            db.add(oauth_cred)
                        
                        db.commit()
                    elif auth_flow == "link":
                        # Linking to existing user
                        user_id = request.session.get("user_id")
                        if not user_id:
                            raise HTTPException(
                                status_code=401,
                                detail="Not authenticated"
                            )
                        
                        # Update Twitter account user_id if not already set
                        if twitter_account.user_id != user_id:
                            twitter_account.user_id = user_id
                        
                        # Store or update OAuth credentials
                        oauth_cred = db.query(TwitterOAuthCredential).filter(
                            TwitterOAuthCredential.twitter_account_id == twitter_id
                        ).first()
                        
                        if oauth_cred:
                            oauth_cred.oauth_token = credentials["oauth_token"]
                            oauth_cred.oauth_token_secret = credentials["oauth_token_secret"]
                            oauth_cred.updated_at = datetime.utcnow()
                        else:
                            oauth_cred = TwitterOAuthCredential(
                                twitter_account_id=twitter_id,
                                oauth_token=credentials["oauth_token"],
                                oauth_token_secret=credentials["oauth_token_secret"]
                            )
                            db.add(oauth_cred)
                        
                        db.commit()
                # Handle new account
                else:
                    if auth_flow == "login":
                        # Create new user and Twitter account
                        user_id = str(uuid.uuid4())
                        username = f"twitter_{credentials['screen_name']}"
                        
                        # Create user
                        user = User(
                            id=user_id,
                            username=username,
                            display_name=credentials.get("name", "")
                        )
                        db.add(user)
                        
                        # Create Twitter account
                        twitter_account = TwitterAccount(
                            twitter_id=twitter_id,
                            user_id=user_id,
                            can_login=True
                        )
                        db.add(twitter_account)
                        
                        # Store OAuth credentials
                        oauth_cred = TwitterOAuthCredential(
                            twitter_account_id=twitter_id,
                            oauth_token=credentials["oauth_token"],
                            oauth_token_secret=credentials["oauth_token_secret"]
                        )
                        db.add(oauth_cred)
                        db.commit()
                        
                        # Set session
                        request.session["user_id"] = user_id
                    elif auth_flow == "link":
                        # Linking to existing user
                        user_id = request.session.get("user_id")
                        if not user_id:
                            raise HTTPException(
                                status_code=401,
                                detail="Not authenticated"
                            )
                        
                        # Create Twitter account
                        twitter_account = TwitterAccount(
                            twitter_id=twitter_id,
                            user_id=user_id,
                            can_login=True
                        )
                        db.add(twitter_account)
                        
                        # Store OAuth credentials
                        oauth_cred = TwitterOAuthCredential(
                            twitter_account_id=twitter_id,
                            oauth_token=credentials["oauth_token"],
                            oauth_token_secret=credentials["oauth_token_secret"]
                        )
                        db.add(oauth_cred)
                        db.commit()
                
                # Clear the session variables related to Twitter auth
                if "twitter_request_token" in request.session:
                    del request.session["twitter_request_token"]
                if "twitter_auth_flow" in request.session:
                    del request.session["twitter_auth_flow"]
                if "twitter_auth_next" in request.session:
                    del request.session["twitter_auth_next"]
                
                # Redirect to next URL
                return RedirectResponse(next_url, status_code=303)
                
            except ValueError as e:
                logger.error(f"Twitter OAuth error: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Twitter OAuth error: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Error processing Twitter OAuth callback: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Error processing Twitter OAuth callback"
                )
        
        @router.get("/link")
        async def twitter_oauth_link(
            request: Request,
            next: str = Query(None),
            callback_url: str = Query(None)
        ):
            """
            Link Twitter account using OAuth.
            
            This endpoint starts the Twitter OAuth flow for linking an account to
            an existing user, redirecting the user to Twitter's authorization page.
            
            Args:
                request (Request): The HTTP request object
                next (str, optional): URL to redirect to after successful linking
                callback_url (str, optional): Custom callback URL for the OAuth flow
                
            Returns:
                RedirectResponse: Redirect to Twitter's authorization page
            """
            # Check if user is logged in
            user_id = request.session.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated"
                )
            
            try:
                # Import Twitter OAuth plugin
                from plugin_manager import plugin_manager
                twitter_oauth = plugin_manager.create_authorization_plugin("twitter_oauth")
                
                if not twitter_oauth:
                    raise HTTPException(
                        status_code=500,
                        detail="Twitter OAuth plugin not available"
                    )
                
                # Get authorization URL and request token
                redirect_url, request_token = await twitter_oauth.get_authorization_url(callback_url)
                
                # Store request token and flow type in session
                request.session["twitter_request_token"] = request_token
                request.session["twitter_auth_flow"] = "link"  # This is a link flow
                
                # Store next URL if provided
                if next:
                    request.session["twitter_auth_next"] = next
                
                # Redirect to Twitter authorization page
                return RedirectResponse(redirect_url)
                
            except Exception as e:
                logger.error(f"Error initiating Twitter OAuth link: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Error initiating Twitter account linking"
                )
        
        return router