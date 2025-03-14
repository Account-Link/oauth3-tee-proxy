"""
Twitter Account Routes
=====================

This module provides RESTful API endpoints for managing Twitter accounts.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from plugins.twitter.models import TwitterAccount, TwitterOAuthCredential

logger = logging.getLogger(__name__)

def create_account_router() -> APIRouter:
    """
    Creates an API router for Twitter account management.
    
    Returns:
        APIRouter: FastAPI router with Twitter account routes
    """
    router = APIRouter(tags=["twitter:accounts"])
    templates = Jinja2Templates(directory="plugins/twitter/templates")
    
    @router.get("/manage", response_class=HTMLResponse)
    async def manage_twitter_accounts(
        request: Request,
        db: Session = Depends(get_db)
    ):
        """
        Render the Twitter accounts management page.
        
        This page shows detailed information about Twitter accounts and 
        allows the user to manage authentication methods (cookie and OAuth).
        
        Args:
            request (Request): The FastAPI request object
            db (Session): Database session dependency
            
        Returns:
            HTMLResponse: The rendered accounts management page
        """
        # Check if user is authenticated via session
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=303)
        
        try:
            # Get all Twitter accounts for this user
            twitter_accounts = db.query(TwitterAccount).filter(
                TwitterAccount.user_id == user_id
            ).all()
            
            # Log for debugging
            for account in twitter_accounts:
                logger.info(f"Twitter account {account.twitter_id}: cookie={repr(account.twitter_cookie)}, username={account.username}")
                
            # Create a dictionary of account IDs to cookie status for all user's accounts
            account_cookie_status = {}
            for account in twitter_accounts:
                # Consider a cookie present if it's not None and not empty
                has_cookie = account.twitter_cookie is not None and account.twitter_cookie != ''
                account_cookie_status[account.twitter_id] = has_cookie
                logger.info(f"Cookie value from DB for {account.twitter_id}: {repr(account.twitter_cookie)}, has_cookie={has_cookie}")
                
            # Get OAuth status for each account
            account_oauth_status = {}
            for account in twitter_accounts:
                oauth_cred = db.query(TwitterOAuthCredential).filter(
                    TwitterOAuthCredential.twitter_account_id == account.twitter_id
                ).first()
                account_oauth_status[account.twitter_id] = oauth_cred
            
            # Add base templates to the search path
            templates.env.loader.searchpath.append("templates")
            
            return templates.TemplateResponse(
                "twitter_accounts.html",
                {
                    "request": request,
                    "twitter_accounts": twitter_accounts,
                    "account_oauth_status": account_oauth_status,
                    "account_cookie_status": account_cookie_status
                }
            )
        except Exception as e:
            logger.error(f"Error rendering Twitter accounts page: {str(e)}", exc_info=True)
            error_message = "Error loading Twitter accounts"
            return RedirectResponse(
                url=f"/error?message={error_message}&back_url=/dashboard",
                status_code=303
            )
            
    @router.delete("/{twitter_id}/cookie")
    async def delete_twitter_cookie(
        twitter_id: str,
        request: Request,
        db: Session = Depends(get_db)
    ):
        """
        Delete the cookie authentication method for a Twitter account.
        
        This endpoint removes only the cookie authentication from a Twitter account
        while keeping the account itself and any OAuth authentication.
        
        Args:
            twitter_id (str): The Twitter ID
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
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "detail": error_message}
                )
            
            # Remove the cookie using SQLAlchemy
            logger.info(f"Deleting cookie for {twitter_id}, current value: {repr(twitter_account.twitter_cookie)}")
            twitter_account.twitter_cookie = None
            db.commit()
            
            logger.info(f"Successfully removed cookie auth for Twitter account {twitter_id}")
            
            # Check if this is an API call based on Accept header
            if request.headers.get("accept") == "application/json":
                return {
                    "status": "success",
                    "message": "Successfully removed cookie authentication",
                    "twitter_id": twitter_id
                }
            else:
                return RedirectResponse(url="/twitter/accounts/manage", status_code=303)
            
        except Exception as e:
            logger.error(f"Error removing cookie auth: {str(e)}", exc_info=True)
            error_message = f"Error removing cookie authentication: {str(e)}"
            if request.headers.get("accept") == "application/json":
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "detail": error_message}
                )
            else:
                return RedirectResponse(
                    url=f"/error?message={error_message}&back_url=/twitter/accounts/manage",
                    status_code=303
                )
                
    @router.delete("/{twitter_id}/oauth")
    async def delete_twitter_oauth(
        twitter_id: str,
        request: Request,
        db: Session = Depends(get_db)
    ):
        """
        Delete the OAuth authentication method for a Twitter account.
        
        This endpoint removes only the OAuth authentication from a Twitter account
        while keeping the account itself and any cookie authentication.
        
        Args:
            twitter_id (str): The Twitter ID
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
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "detail": error_message}
                )
            
            # Find and delete the OAuth credentials
            oauth_cred = db.query(TwitterOAuthCredential).filter(
                TwitterOAuthCredential.twitter_account_id == twitter_id
            ).first()
            
            if oauth_cred:
                db.delete(oauth_cred)
                db.commit()
                logger.info(f"Successfully removed OAuth auth for Twitter account {twitter_id}")
            else:
                logger.warning(f"No OAuth credentials found for Twitter account {twitter_id}")
            
            # Check if this is an API call based on Accept header
            if request.headers.get("accept") == "application/json":
                return {
                    "status": "success",
                    "message": "Successfully removed OAuth authentication",
                    "twitter_id": twitter_id
                }
            else:
                return RedirectResponse(url="/twitter/accounts/manage", status_code=303)
            
        except Exception as e:
            logger.error(f"Error removing OAuth auth: {str(e)}", exc_info=True)
            error_message = f"Error removing OAuth authentication: {str(e)}"
            if request.headers.get("accept") == "application/json":
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "detail": error_message}
                )
            else:
                return RedirectResponse(
                    url=f"/error?message={error_message}&back_url=/twitter/accounts/manage",
                    status_code=303
                )
    
    @router.delete("/{twitter_id}")
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
            
    @router.delete("/")
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
            Dict[str, Any]: Status message
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