# plugins/twitter/resource.py
"""
Twitter Resource Plugin for OAuth3 TEE Proxy
===========================================

This module implements the Twitter resource plugin for the OAuth3 TEE Proxy.
It handles interaction with the Twitter API on behalf of users, providing
functionality for posting tweets and other Twitter operations.

The TwitterResourcePlugin class implements the ResourcePlugin interface,
providing methods for:
- Initializing Twitter API clients with user credentials
- Validating Twitter API clients
- Defining available scopes for Twitter operations
- Posting tweets using the Twitter API

The plugin uses the TwitterClient wrapper class that encapsulates the
interaction with the Twitter API, providing a simplified interface for
common operations and handling errors in a consistent way.

Supported Scopes:
---------------
- tweet.post: Permission to post tweets
- tweet.read: Permission to read tweets
- tweet.delete: Permission to delete tweets
"""

import logging
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Security, Form, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from plugins.twitter.models import TwitterAccount, TweetLog
from oauth2_routes import OAuth2Token, verify_token_and_scopes
from safety import SafetyFilter, SafetyLevel
from plugins.twitter.config import get_twitter_settings
from plugins import ResourcePlugin, RoutePlugin
from twitter.account import Account

logger = logging.getLogger(__name__)
settings = get_twitter_settings()

# Pydantic models
class TwitterCookieSubmit(BaseModel):
    """Model for submitting Twitter cookie."""
    twitter_cookie: str

class TweetRequest(BaseModel):
    """Model for tweet requests."""
    text: str
    bypass_safety: bool = False

class TwitterClient:
    """
    Twitter client wrapper used by the resource plugin.
    
    This class wraps the twitter.account.Account class, providing a simplified
    interface for interacting with the Twitter API. It handles errors and provides
    async-compatible methods for common Twitter operations.
    
    The TwitterClient is created by the TwitterResourcePlugin using the credentials
    stored in the database. It is responsible for making API calls to Twitter and
    handling the responses.
    
    Attributes:
        account (Account): The underlying Twitter Account object used for API calls
    """
    
    def __init__(self, account: Account):
        """
        Initialize with a Twitter Account object.
        
        Args:
            account (Account): The Twitter Account object to use for API calls
        """
        self.account = account
    
    async def validate(self) -> bool:
        """
        Validate if the client is still working.
        
        Makes a lightweight API call to Twitter to check if the client's credentials
        are still valid. Returns True if the call succeeds, False otherwise.
        
        Returns:
            bool: True if the client is valid, False otherwise
        """
        try:
            self.account.bookmarks(limit=1)
            return True
        except Exception as e:
            logger.error(f"Error validating Twitter client: {e}")
            return False
            
    async def post_tweet(self, text: str) -> str:
        """
        Post a tweet and return the tweet ID.
        
        Posts a tweet with the given text using the Twitter API and returns
        the ID of the newly created tweet.
        
        Args:
            text (str): The text of the tweet to post
            
        Returns:
            str: The ID of the posted tweet
            
        Raises:
            ValueError: If the tweet ID cannot be extracted from the response
            Exception: If any other error occurs during the operation
        """
        try:
            response = self.account.tweet(text)
            logger.debug(f"Tweet response: {response}")
            
            tweet_data = response.get('data', {})
            tweet_id = str(tweet_data.get('id_str') or tweet_data.get('id'))
            
            if not tweet_id:
                raise ValueError("Could not extract tweet ID from response")
                
            return tweet_id
        except Exception as e:
            logger.error(f"Error posting tweet: {e}\nTraceback:\n{traceback.format_exc()}")
            raise

class TwitterResourcePlugin(ResourcePlugin, RoutePlugin):
    """
    Plugin for Twitter resource operations.
    
    This class implements the ResourcePlugin and RoutePlugin interfaces for Twitter operations,
    providing methods for initializing Twitter clients, validating clients,
    and performing operations like posting tweets.
    
    The plugin defines the available scopes for Twitter operations and provides
    methods for working with these scopes. It serves as a bridge between the
    OAuth3 TEE Proxy and the Twitter API.
    
    It also provides routes for Twitter-specific operations that are mounted
    under the "/twitter" prefix in the main application.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin ("twitter")
        SCOPES (Dict[str, str]): Dictionary mapping scope names to descriptions
    """
    
    service_name = "twitter"
    
    SCOPES = {
        "tweet.post": "Permission to post tweets",
        "tweet.read": "Permission to read tweets",
        "tweet.delete": "Permission to delete tweets" 
    }
    
    async def initialize_client(self, credentials: Dict[str, Any]) -> TwitterClient:
        """
        Initialize Twitter client with credentials.
        
        Creates a new TwitterClient instance using the provided credentials.
        This method is called by the TEE Proxy when it needs to make Twitter
        API calls on behalf of a user.
        
        Args:
            credentials (Dict[str, Any]): The Twitter cookie credentials
            
        Returns:
            TwitterClient: An initialized Twitter client
            
        Raises:
            Exception: If the client cannot be initialized
        """
        try:
            account = Account(cookies=credentials)
            return TwitterClient(account)
        except Exception as e:
            logger.error(f"Error initializing Twitter client: {e}")
            raise
    
    async def validate_client(self, client: TwitterClient) -> bool:
        """
        Validate if the Twitter client is still valid.
        
        Checks if the Twitter client's credentials are still valid by making
        a lightweight API call to Twitter.
        
        Args:
            client (TwitterClient): The client to validate
            
        Returns:
            bool: True if the client is valid, False otherwise
        """
        return await client.validate()
    
    def get_available_scopes(self) -> List[str]:
        """
        Get the list of scopes supported by this resource plugin.
        
        Returns the list of scope names that can be requested for Twitter
        operations. These scopes define the permissions that clients can
        request when accessing Twitter resources.
        
        Returns:
            List[str]: List of scope strings
        """
        return list(self.SCOPES.keys())
    
    async def post_tweet(self, client: TwitterClient, text: str) -> str:
        """
        Post a tweet using the client.
        
        Posts a tweet with the given text using the provided TwitterClient.
        This method is called by the TEE Proxy when a client with the
        'tweet.post' scope requests to post a tweet.
        
        Args:
            client (TwitterClient): The Twitter client to use
            text (str): The text of the tweet to post
            
        Returns:
            str: The ID of the posted tweet
            
        Raises:
            Exception: If the tweet cannot be posted
        """
        return await client.post_tweet(text)
    
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
                twitter_auth = plugin_manager.create_authorization_plugin("twitter")
                if not twitter_auth:
                    raise HTTPException(
                        status_code=500,
                        detail="Twitter plugin not available"
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
                
                # Get the authorization plugin to parse credentials
                from plugin_manager import plugin_manager
                twitter_auth = plugin_manager.create_authorization_plugin("twitter")
                
                # Get credentials and initialize client
                credentials = twitter_auth.credentials_from_string(twitter_account.twitter_cookie)
                client = await self.initialize_client(credentials)
                
                # Post tweet
                tweet_id = await self.post_tweet(client, tweet_data.text)
                
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