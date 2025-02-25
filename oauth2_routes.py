from fastapi import APIRouter, Depends, HTTPException, Security, Request, Form
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

from models import OAuth2Token, User
from database import get_db
from config import get_settings

router = APIRouter()
settings = get_settings()

# Define available scopes
OAUTH2_SCOPES = {
    "telegram.post_any": "Permission to post any message to Telegram",
    "tweet.post": "Permission to post tweets"
}

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes=OAUTH2_SCOPES
)

async def verify_token_and_scopes(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):  
    import sys
    print(f"Verifying token: {token}", flush=True, file=sys.stderr)
    print(f"Requested scopes: {security_scopes.scopes}", flush=True, file=sys.stderr)
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
        raise credentials_exception

    # Check if token has expired
    if token_record.expires_at and token_record.expires_at < datetime.utcnow():
        raise credentials_exception

    # Verify scopes
    token_scopes = set(token_record.scopes.split())
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
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
    allowed_scopes = set(settings.OAUTH2_ALLOWED_SCOPES.split())
    
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