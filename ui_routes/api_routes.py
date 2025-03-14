"""
API Token Routes
==============

This module provides routes for API token management, enabling users to:
- Create new API tokens with selected scopes
- View and manage API tokens
- Revoke tokens
"""

import logging
from typing import List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, JWTToken
from auth.jwt_service import create_token, revoke_token
from auth.middleware import get_current_user

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["API Tokens"])

# Available scopes - will be populated from plugins
AVAILABLE_SCOPES = {
    "tweet.post": "Post tweets to Twitter",
    "telegram.post_any": "Post to any connected Telegram channel",
    # More scopes will be added by plugins
}

# Pydantic models for request validation
class TokenCreateRequest(BaseModel):
    """Request model for creating an API token."""
    scopes: List[str]
    description: Optional[str] = None
    expiry_hours: Optional[int] = 48  # Default to 48 hours

class TokenResponse(BaseModel):
    """Response model for token information."""
    token_id: str
    access_token: str
    scopes: List[str]
    expires_at: str
    policy: str

@router.get("/tokens")
async def list_tokens(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all active API tokens for the user."""
    tokens = db.query(JWTToken).filter(
        JWTToken.user_id == user.id,
        JWTToken.is_active == True,
        JWTToken.policy == "api"
    ).all()
    
    result = []
    for token in tokens:
        result.append({
            "token_id": token.token_id,
            "scopes": token.scopes.split() if token.scopes else [],
            "created_at": token.created_at.isoformat(),
            "expires_at": token.expires_at.isoformat(),
            "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None
        })
    
    return {"tokens": result}

@router.post("/tokens", response_model=TokenResponse)
async def create_api_token(
    request: Request,
    token_request: TokenCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new API token with the requested scopes."""
    # Validate scopes
    for scope in token_request.scopes:
        if scope not in AVAILABLE_SCOPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scope: {scope}"
            )
    
    # Limit expiry hours to reasonable range
    expiry_hours = token_request.expiry_hours
    if expiry_hours < 1:
        expiry_hours = 1
    elif expiry_hours > 720:  # Max 30 days
        expiry_hours = 720
    
    # Create token
    token_data = create_token(
        user_id=user.id,
        policy="api",
        scopes=token_request.scopes,
        db=db,
        request=request,
        expiry_hours=expiry_hours
    )
    
    # Update token with description if provided
    if token_request.description:
        token = db.query(JWTToken).filter(
            JWTToken.token_id == token_data["token_id"]
        ).first()
        
        if token:
            # Store description in the user_agent field (repurposing for API tokens)
            token.user_agent = token_request.description
            db.commit()
    
    return {
        "token_id": token_data["token_id"],
        "access_token": token_data["token"],
        "scopes": token_request.scopes,
        "expires_at": token_data["expires_at"].isoformat(),
        "policy": "api"
    }

@router.delete("/tokens/{token_id}")
async def delete_api_token(
    token_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an API token."""
    # Verify token belongs to user and is an API token
    token = db.query(JWTToken).filter(
        JWTToken.token_id == token_id,
        JWTToken.user_id == user.id,
        JWTToken.policy == "api",
        JWTToken.is_active == True
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=404,
            detail="Token not found or not an active API token"
        )
    
    # Revoke token
    revoke_token(
        token_id=token_id,
        user_id=user.id,
        db=db,
        request=request
    )
    
    return {"success": True, "message": "Token revoked successfully"}

# Function to update available scopes from plugins
def update_available_scopes(plugin_scopes: dict):
    """Update available scopes from plugins."""
    global AVAILABLE_SCOPES
    AVAILABLE_SCOPES.update(plugin_scopes)