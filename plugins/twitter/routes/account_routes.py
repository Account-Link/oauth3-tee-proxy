"""
Twitter Account Routes
=====================

This module provides RESTful API endpoints for managing Twitter accounts.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from plugins.twitter.models import TwitterAccount

logger = logging.getLogger(__name__)

def create_account_router() -> APIRouter:
    """
    Creates an API router for Twitter account management.
    
    Returns:
        APIRouter: FastAPI router with Twitter account routes
    """
    router = APIRouter(tags=["twitter:accounts"])
    
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