"""
JWT Token Service
===============

This module provides functions for creating, validating, and managing JWT tokens
for authentication. It handles token creation, validation, revocation, and refresh.

The service follows these principles:
- Tokens expire after 2 hours by default
- Tokens contain minimal user information (user_id, policy, token_id)
- Tokens can be revoked individually or all for a user
- Session tokens are automatically refreshed if expiring within 30 minutes
"""

import jwt
import uuid
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import Request, Response

from config import get_settings
from models import User, JWTToken, AuthAccessLog
from database import get_db

# Get settings
settings = get_settings()

# Set up logger
logger = logging.getLogger(__name__)

def create_token(
    user_id: str,
    policy: str = "passkey",
    scopes: Optional[List[str]] = None,
    db: Session = None,
    request: Optional[Request] = None,
    expiry_hours: int = 2
) -> Dict[str, Any]:
    """
    Create a new JWT token for a user.
    
    Args:
        user_id: The ID of the user
        policy: The policy for this token (passkey, api, etc.)
        scopes: Optional list of scopes for API tokens
        db: Database session
        request: Optional request object for logging IP/user agent
        expiry_hours: Token expiration hours (default 2)
        
    Returns:
        Dict with token data including the encoded token
    """
    if db is None:
        db = next(get_db())
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    # Create token ID
    token_id = str(uuid.uuid4())
    
    # Token expiration time
    expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
    
    # Create payload
    payload = {
        "sub": user_id,
        "policy": policy,
        "jti": token_id,
        "exp": expires_at.timestamp()
    }
    
    # Add scopes if provided
    if scopes:
        payload["scopes"] = " ".join(scopes)
    
    # Create encoded token
    encoded_token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    
    # Extract client info if request provided
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
    
    # Store token in database
    token_record = JWTToken(
        token_id=token_id,
        user_id=user_id,
        policy=policy,
        scopes=" ".join(scopes) if scopes else None,
        expires_at=expires_at,
        created_by_ip=ip_address,
        user_agent=user_agent
    )
    db.add(token_record)
    
    # Log token creation
    log_entry = AuthAccessLog(
        user_id=user_id,
        token_id=token_id,
        action="token_create",
        ip_address=ip_address,
        user_agent=user_agent,
        details=f"Policy: {policy}"
    )
    db.add(log_entry)
    db.commit()
    
    return {
        "token": encoded_token,
        "token_id": token_id,
        "expires_at": expires_at,
        "policy": policy
    }

def validate_token(
    token: str,
    db: Session = None,
    request: Optional[Request] = None,
    log_access: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Validate a JWT token and return the token data.
    
    Args:
        token: The JWT token to validate
        db: Database session
        request: Optional request object for logging
        log_access: Whether to log this access (default True)
        
    Returns:
        Dict with token data and user if valid, None otherwise
    """
    if db is None:
        db = next(get_db())
    
    try:
        # Decode token without verification first to get the token ID
        unverified_payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        
        token_id = unverified_payload.get("jti")
        if not token_id:
            logger.warning("Token missing jti claim")
            return None
            
        # Check if token exists and is active
        token_record = db.query(JWTToken).filter(
            JWTToken.token_id == token_id,
            JWTToken.is_active == True
        ).first()
        
        if not token_record:
            logger.warning(f"Token {token_id} not found or inactive")
            return None
            
        # Now verify the token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        
        # Get user
        user_id = payload["sub"]
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.warning(f"User {user_id} for token {token_id} not found")
            return None
            
        # Update last used time
        token_record.last_used_at = datetime.utcnow()
        
        # Log access if requested
        if log_access:
            ip_address = None
            user_agent = None
            if request:
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("User-Agent")
                
            log_entry = AuthAccessLog(
                user_id=user_id,
                token_id=token_id,
                action="token_use",
                ip_address=ip_address,
                user_agent=user_agent,
                details=f"Policy: {token_record.policy}"
            )
            db.add(log_entry)
            
        db.commit()
        
        # Return token data with user
        return {
            "token_id": token_id,
            "user_id": user_id,
            "policy": payload.get("policy"),
            "scopes": payload.get("scopes", "").split() if "scopes" in payload else [],
            "expires_at": datetime.fromtimestamp(payload["exp"]),
            "user": user,
            "token_record": token_record
        }
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        return None

def refresh_token_if_needed(
    token_data: Dict[str, Any],
    request: Request,
    response: Response,
    refresh_threshold_minutes: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Check if a token is about to expire and refresh it if needed.
    
    Args:
        token_data: Token data from validate_token
        request: The request object
        response: The response object to set cookies on
        refresh_threshold_minutes: Minutes before expiry to refresh (default 30)
        
    Returns:
        New token data if refreshed, None otherwise
    """
    # Check if token is about to expire
    expires_at = token_data["expires_at"]
    now = datetime.utcnow()
    
    # If token expires within threshold, refresh it
    if expires_at - now < timedelta(minutes=refresh_threshold_minutes):
        db = next(get_db())
        
        # Get info from current token
        user_id = token_data["user_id"]
        policy = token_data["policy"]
        scopes = token_data["scopes"]
        
        # Create new token
        new_token_data = create_token(
            user_id=user_id,
            policy=policy,
            scopes=scopes,
            db=db,
            request=request
        )
        
        # Set new token in cookie if using session
        if policy == "passkey" and request.cookies.get("access_token"):
            response.set_cookie(
                key="access_token",
                value=new_token_data["token"],
                httponly=True,
                max_age=7200,  # 2 hours
                samesite="lax",
                secure=settings.PRODUCTION
            )
            
        # Log token refresh
        log_entry = AuthAccessLog(
            user_id=user_id,
            token_id=new_token_data["token_id"],
            action="token_refresh",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
        db.add(log_entry)
        db.commit()
        
        return new_token_data
    
    return None

def revoke_token(
    token_id: str,
    user_id: str,
    db: Session = None,
    request: Optional[Request] = None
) -> bool:
    """
    Revoke a specific token.
    
    Args:
        token_id: The ID of the token to revoke
        user_id: The ID of the user who owns the token
        db: Database session
        request: Optional request object for logging
        
    Returns:
        True if token was revoked, False otherwise
    """
    if db is None:
        db = next(get_db())
    
    # Find token
    token = db.query(JWTToken).filter(
        JWTToken.token_id == token_id,
        JWTToken.user_id == user_id,
        JWTToken.is_active == True
    ).first()
    
    if not token:
        return False
    
    # Revoke token
    token.is_active = False
    token.revoked_at = datetime.utcnow()
    
    # Log revocation
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
    log_entry = AuthAccessLog(
        user_id=user_id,
        token_id=token_id,
        action="token_revoke",
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(log_entry)
    db.commit()
    
    return True

def revoke_all_user_tokens(
    user_id: str,
    db: Session = None,
    request: Optional[Request] = None,
    exclude_token_id: Optional[str] = None
) -> int:
    """
    Revoke all tokens for a user except the current one.
    
    Args:
        user_id: The ID of the user
        db: Database session
        request: Optional request object for logging
        exclude_token_id: Optional token ID to exclude (current token)
        
    Returns:
        Number of tokens revoked
    """
    if db is None:
        db = next(get_db())
    
    # Build query
    query = db.query(JWTToken).filter(
        JWTToken.user_id == user_id,
        JWTToken.is_active == True
    )
    
    # Exclude current token if specified
    if exclude_token_id:
        query = query.filter(JWTToken.token_id != exclude_token_id)
    
    # Get tokens to revoke
    tokens = query.all()
    
    if not tokens:
        return 0
    
    # Revoke all tokens
    for token in tokens:
        token.is_active = False
        token.revoked_at = datetime.utcnow()
    
    # Log the mass revocation
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
    
    log_entry = AuthAccessLog(
        user_id=user_id,
        action="token_revoke_all",
        ip_address=ip_address,
        user_agent=user_agent,
        details=f"Revoked {len(tokens)} tokens"
    )
    db.add(log_entry)
    db.commit()
    
    return len(tokens)