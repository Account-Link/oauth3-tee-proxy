"""
OAuth2 Routes for JWT Authentication
====================================

This module implements the OAuth2 authentication routes and utilities for JWT token
verification and scope checking in the OAuth3 TEE Proxy application.
"""

import logging
from typing import List, Optional, Union
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import SecurityScopes, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import OAuth2Token, User
from safety import decode_jwt_token

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "twitter.read": "Read access to Twitter API",
        "twitter.write": "Write access to Twitter API",
        "twitter.graphql": "Access to Twitter GraphQL API",
        "twitter.graphql.read": "Read access to Twitter GraphQL API",
        "twitter.graphql.write": "Write access to Twitter GraphQL API",
        "telegram.read": "Read access to Telegram API",
        "telegram.write": "Write access to Telegram API",
    }
)

async def verify_token_and_scopes(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> OAuth2Token:
    """
    Verify a JWT token and check if it has the required scopes.
    
    This function is used as a dependency in routes that require OAuth2 authentication
    with specific scopes. It verifies the JWT token, checks if it's still active in 
    the database, and validates that it has the required scopes.
    
    Args:
        security_scopes (SecurityScopes): The scopes required for the route
        token (str): The JWT token from the Authorization header
        db (Session): Database session
        
    Returns:
        OAuth2Token: The OAuth2 token object from the database
        
    Raises:
        HTTPException: If the token is invalid, expired, or doesn't have required scopes
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{" ".join(security_scopes.scopes)}"'
    else:
        authenticate_value = "Bearer"
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        # Decode the JWT token
        payload = decode_jwt_token(token)
        if payload is None:
            logger.warning("Invalid token format")
            raise credentials_exception
            
        token_id: str = payload.get("token_id")
        if token_id is None:
            logger.warning("Token ID not found in JWT payload")
            raise credentials_exception
            
        # Get the token from the database
        oauth2_token = db.query(OAuth2Token).filter(
            OAuth2Token.id == token_id,
            OAuth2Token.is_active == True,
            OAuth2Token.expires_at > datetime.utcnow()
        ).first()
        
        if oauth2_token is None:
            logger.warning(f"Token {token_id} not found or inactive")
            raise credentials_exception
            
        # Check if the token has the required scopes
        token_scopes = set(oauth2_token.scopes.split() if oauth2_token.scopes else [])
        
        for scope in security_scopes.scopes:
            if scope not in token_scopes:
                logger.warning(
                    f"Token {token_id} missing required scope: {scope}. "
                    f"Token scopes: {token_scopes}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required scope: {scope}",
                    headers={"WWW-Authenticate": authenticate_value},
                )
                
        return oauth2_token
        
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise credentials_exception