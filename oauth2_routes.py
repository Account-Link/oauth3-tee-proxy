from fastapi import APIRouter, Depends, HTTPException, Security, Request, Form
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import logging

from models import OAuth2Token, User
from database import get_db
from config import get_settings
from plugin_manager import plugin_manager

# Import plugin-specific settings to get allowed scopes
from plugins.twitter.config import get_twitter_settings
from plugins.telegram.config import get_telegram_settings

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

# Define available scopes
# Scopes will be populated dynamically from plugins
OAUTH2_SCOPES = {}

# Function to update scopes from plugins - will be called after plugins are loaded
def update_scopes_from_plugins():
    """
    Update OAuth2 scopes from registered plugins.
    
    This function is called after all plugins are loaded to update the
    OAUTH2_SCOPES dictionary with scopes from all resource plugins.
    It retrieves the scopes from the plugin_manager and adds them to
    the global OAUTH2_SCOPES dictionary.
    
    The function also validates that the plugin-defined scopes match
    what's allowed in each plugin's configuration.
    
    The function should be called during application startup, after
    plugin discovery but before the application starts handling requests.
    
    Side Effects:
        Updates the global OAUTH2_SCOPES dictionary with plugin scopes.
        Logs information about the number of scopes registered.
    """
    global OAUTH2_SCOPES
    
    # Get scopes from all plugins through the plugin manager
    plugin_scopes = plugin_manager.get_all_plugin_scopes()
    OAUTH2_SCOPES.update(plugin_scopes)
    
    # Also validate plugin-specific scope settings
    # This ensures that plugin configs ALLOWED_SCOPES setting matches what the plugin registers
    twitter_settings = get_twitter_settings()
    telegram_settings = get_telegram_settings()
    
    twitter_scopes = set(twitter_settings.ALLOWED_SCOPES.split())
    telegram_scopes = set(telegram_settings.ALLOWED_SCOPES.split())
    
    registered_twitter_scopes = {s for s in OAUTH2_SCOPES if s.startswith("tweet.")}
    registered_telegram_scopes = {s for s in OAUTH2_SCOPES if s.startswith("telegram.")}
    
    # Log warnings if there are mismatches
    for scope in twitter_scopes:
        if scope not in registered_twitter_scopes:
            logger.warning(f"Twitter scope '{scope}' in settings but not registered by plugin")
    
    for scope in telegram_scopes:
        if scope not in registered_telegram_scopes:
            logger.warning(f"Telegram scope '{scope}' in settings but not registered by plugin")
    
    logger.info(f"Updated OAuth2 scopes from plugins: {len(OAUTH2_SCOPES)} scopes registered")

# Define the oauth2_scheme with empty scopes for now
# It will be updated after plugin loading
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes=OAUTH2_SCOPES
)

async def verify_token_and_scopes(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):  
    """
    Verify an OAuth2 token and check if it has the required scopes.
    
    This function is used as a dependency for protected endpoints to validate
    the OAuth2 token provided in the request and check if it has the required
    scopes for the requested operation.
    
    The function performs the following checks:
    1. Verifies that the token exists in the database and is active
    2. Checks if the token has expired
    3. Verifies that the token has all the required scopes
    
    Args:
        security_scopes (SecurityScopes): The scopes required for the endpoint
        token (str): The OAuth2 token from the request header
        db (Session): The database session
        
    Returns:
        OAuth2Token: The token record from the database if validation is successful
        
    Raises:
        HTTPException: If the token is invalid, expired, or lacks required scopes
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )

    # Get token from database
    token_record = db.query(OAuth2Token).filter(
        OAuth2Token.access_token == token,
        OAuth2Token.is_active == True
    ).first()
    
    if not token_record:
        logger.warning(f"Invalid or inactive token attempted to be used")
        raise credentials_exception

    # Check if token has expired
    if token_record.expires_at and token_record.expires_at < datetime.utcnow():
        logger.warning(f"Expired token attempted to be used")
        raise credentials_exception

    # Verify scopes
    token_scopes = set(token_record.scopes.split())
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            logger.warning(f"Token missing required scope: {scope}")
            raise HTTPException(
                status_code=401,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )

    return token_record

@router.post("/token")
async def create_token(
    request: Request,
    scopes: str = Form(...),  # Space separated scopes
    db: Session = Depends(get_db)
):
    """
    Create a new OAuth2 access token with the requested scopes.
    
    This endpoint allows users to create OAuth2 access tokens that can be used
    to authenticate API requests to the TEE Proxy. The tokens are scoped to
    specific permissions requested by the client.
    
    The function performs the following steps:
    1. Verifies that the user is authenticated via session
    2. Validates that the requested scopes are allowed
    3. Creates a new OAuth2 token with the requested scopes
    4. Returns the token details to the client
    
    Args:
        request (Request): The HTTP request object
        scopes (str): Space-separated list of requested scopes
        db (Session): The database session
        
    Returns:
        dict: Dictionary containing token details:
            - access_token: The token string
            - token_type: Always "bearer"
            - scope: The granted scopes
            - expires_in: Token lifetime in seconds
            
    Raises:
        HTTPException: If authentication fails or requested scopes are invalid
    """
    # Check if user is authenticated via session
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Must be account owner to request tokens."
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )
    
    # Validate requested scopes
    requested_scopes = set(scopes.split())
    allowed_scopes = set(OAUTH2_SCOPES.keys())
    
    if not requested_scopes.issubset(allowed_scopes):
        raise HTTPException(
            status_code=400,
            detail="Invalid scopes requested"
        )
    
    # Create OAuth2 token
    token = OAuth2Token(
        access_token=str(uuid.uuid4()),
        scopes=scopes,
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(hours=settings.OAUTH2_TOKEN_EXPIRE_HOURS)
    )
    db.add(token)
    db.commit()
    
    return {
        "access_token": token.access_token,
        "token_type": "bearer",
        "scope": scopes,
        "expires_in": settings.OAUTH2_TOKEN_EXPIRE_HOURS * 3600
    }

@router.delete("/token/{token_id}")
async def revoke_token(
    token_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Revoke an OAuth2 access token.
    
    This endpoint allows users to revoke previously issued OAuth2 tokens,
    preventing them from being used for future API requests. The token's
    is_active flag is set to False, but the token record is retained
    for audit purposes.
    
    The function performs the following steps:
    1. Verifies that the user is authenticated via session
    2. Verifies that the token exists and belongs to the authenticated user
    3. Sets the token's is_active flag to False
    
    Args:
        token_id (str): The ID of the token to revoke
        request (Request): The HTTP request object
        db (Session): The database session
        
    Returns:
        dict: Status message indicating success
        
    Raises:
        HTTPException: If authentication fails or the token is not found
    """
    # Check if user is authenticated via session
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    # Get token
    token = db.query(OAuth2Token).filter(
        OAuth2Token.token_id == token_id,
        OAuth2Token.user_id == user_id,
        OAuth2Token.is_active == True
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=404,
            detail="Token not found"
        )
    
    # Revoke token
    token.is_active = False
    db.commit()
    
    return {"status": "success", "message": "Token revoked"} 