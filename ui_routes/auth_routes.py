"""
Authentication Routes
===================

This module defines the routes for user authentication, including:
- Passkey registration and login
- Profile management
- Session management
"""

import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, Request, Response, HTTPException, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator, EmailStr

from database import get_db
from models import User, WebAuthnCredential, JWTToken, AuthAccessLog
from auth.passkey_service import PasskeyService, get_passkey_service
from auth.jwt_service import revoke_token, revoke_all_user_tokens
from auth.middleware import get_current_user

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Templates
templates = Jinja2Templates(directory="templates")

# Pydantic models for request validation
class RegisterRequest(BaseModel):
    """Request model for starting passkey registration."""
    username: Optional[str] = None
    display_name: Optional[str] = None
    
    @validator('username')
    def username_must_be_valid(cls, v):
        if v is not None:
            if len(v) < 3:
                raise ValueError('Username must be at least 3 characters')
            if not v.isalnum() and not '-' in v and not '_' in v:
                raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v

class CredentialResponse(BaseModel):
    """Model for credential data in responses."""
    credential: Dict[str, Any]
    client_data: Optional[str] = None
    
    class Config:
        # Allow extra fields for flexibility
        extra = "allow"

class ProfileUpdateRequest(BaseModel):
    """Request model for updating user profile."""
    username: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    wallet_address: Optional[str] = None
    
    @validator('username')
    def username_must_be_valid(cls, v):
        if v is not None:
            if len(v) < 3:
                raise ValueError('Username must be at least 3 characters')
            if not v.isalnum() and not '-' in v and not '_' in v:
                raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v
    
    @validator('phone_number')
    def phone_number_must_be_valid(cls, v):
        if v is not None:
            # Simple validation for now
            if not v.startswith('+') or not v[1:].isdigit() or len(v) < 8:
                raise ValueError('Phone number must be in international format (e.g., +12345678901)')
        return v
    
    @validator('wallet_address')
    def wallet_address_must_be_valid(cls, v):
        if v is not None:
            # Basic Ethereum address validation
            if not v.startswith('0x') or len(v) != 42:
                raise ValueError('Wallet address must be a valid Ethereum address (0x...)')
        return v

class DeviceNameRequest(BaseModel):
    """Request model for device name operations."""
    device_name: str
    
    @validator('device_name')
    def device_name_must_be_valid(cls, v):
        if len(v) < 1 or len(v) > 50:
            raise ValueError('Device name must be between 1 and 50 characters')
        return v

# Registration routes
@router.get("/register")
async def register_page(request: Request):
    """Render the registration page."""
    # Use the regular register.html template which has all the JavaScript properly defined
    # Create this if it doesn't exist yet
    try:
        # Try the new template first
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "title": "Register with Passkey"}
        )
    except Exception as e:
        # Fall back to webauthn_register.html
        logger.error(f"Error rendering register.html: {str(e)}")
        return templates.TemplateResponse(
            "webauthn_register.html",
            {"request": request, "title": "Register with Passkey"}
        )

@router.post("/register/begin")
async def start_registration(
    request: Request,
    registration_request: RegisterRequest,
    passkey_service: PasskeyService = Depends(get_passkey_service),
    db: Session = Depends(get_db)
):
    """Start passkey registration process."""
    try:
        options, _ = passkey_service.start_registration(
            request=request,
            db=db,
            username=registration_request.username,
            display_name=registration_request.display_name
        )
        return options
    except Exception as e:
        logger.error(f"Registration start failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register/complete")
async def complete_registration(
    request: Request,
    response: Response,
    credential_response: CredentialResponse = None,
    device_name: Optional[str] = Form(None),
    passkey_service: PasskeyService = Depends(get_passkey_service),
    db: Session = Depends(get_db)
):
    """Complete passkey registration process."""
    try:
        # Handle the case where credential_response is None
        if credential_response is None:
            import json
            try:
                # Try to parse JSON directly from the body
                body = await request.body()
                data = json.loads(body)
                
                if 'credential' in data:
                    credential_data = data['credential']
                else:
                    raise HTTPException(status_code=400, detail="Missing credential data in request")
            except Exception as parse_error:
                logger.error(f"Error parsing registration request: {str(parse_error)}")
                raise HTTPException(status_code=400, detail=f"Failed to parse request: {str(parse_error)}") 
        else:
            credential_data = credential_response.credential
        
        # Now call the service with the credential data
        result = passkey_service.complete_registration(
            request=request,
            db=db,
            credential_data=credential_data,
            device_name=device_name
        )
        
        # Set token in cookie
        response.set_cookie(
            key="access_token",
            value=result["token"],
            httponly=True,
            max_age=7200,  # 2 hours
            samesite="lax",
            secure=False  # Set to True in production with HTTPS
        )
        
        return {"success": True, "redirect": "/profile"}
    except Exception as e:
        logger.error(f"Registration completion failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Login routes
@router.get("/login")
async def login_page(request: Request):
    """Render the login page."""
    # Use the regular login.html template which has all the JavaScript properly defined
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "title": "Login with Passkey"}
    )

@router.post("/login/begin")
async def start_login(
    request: Request,
    username: Optional[str] = Form(None),
    passkey_service: PasskeyService = Depends(get_passkey_service),
    db: Session = Depends(get_db)
):
    """Start passkey login process."""
    try:
        # Try to extract username from JSON body if not provided as form data
        if not username and request.headers.get('content-type') == 'application/json':
            import json
            try:
                body = await request.body()
                data = json.loads(body)
                username = data.get('username')
            except Exception as parse_error:
                logger.error(f"Error parsing login request body: {str(parse_error)}")
        
        # Start authentication with passkey service
        options = passkey_service.start_authentication(
            request=request,
            db=db,
            username=username
        )
        
        # For form submissions, return HTML with redirect
        if request.headers.get('content-type', '').startswith('multipart/form-data'):
            return HTMLResponse(f"""
                <html>
                <head>
                    <meta http-equiv="refresh" content="0;url=/auth/login?options={options}">
                </head>
                <body>Redirecting...</body>
                </html>
            """)
            
        return options
    except Exception as e:
        logger.error(f"Login start failed: {str(e)}")
        logger.error(f"Login error details:", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login/complete")
async def complete_login(
    request: Request,
    response: Response,
    credential_response: CredentialResponse = None,
    passkey_service: PasskeyService = Depends(get_passkey_service),
    db: Session = Depends(get_db)
):
    """Complete passkey login process."""
    try:
        # Handle the case where credential_response is None
        if credential_response is None:
            import json
            try:
                # Try to parse JSON directly from the body
                body = await request.body()
                data = json.loads(body)
                
                if 'credential' in data:
                    credential_data = data['credential']
                else:
                    raise HTTPException(status_code=400, detail="Missing credential data in request")
            except Exception as parse_error:
                logger.error(f"Error parsing login complete request: {str(parse_error)}")
                raise HTTPException(status_code=400, detail=f"Failed to parse request: {str(parse_error)}") 
        else:
            credential_data = credential_response.credential
        
        # Complete authentication process
        result = passkey_service.complete_authentication(
            request=request,
            db=db,
            credential_data=credential_data
        )
        
        # Set token in cookie
        response.set_cookie(
            key="access_token",
            value=result["token"],
            httponly=True,
            max_age=7200,  # 2 hours
            samesite="lax",
            secure=False  # Set to True in production with HTTPS
        )
        
        return {"success": True, "redirect": "/profile"}
    except Exception as e:
        logger.error(f"Login completion failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Log out the current user by revoking their token."""
    token = request.cookies.get("access_token")
    if token:
        from auth.jwt_service import validate_token
        token_data = validate_token(token, db, request, log_access=False)
        if token_data:
            # Revoke token
            revoke_token(
                token_id=token_data["token_id"],
                user_id=token_data["user_id"],
                db=db,
                request=request
            )
    
    # Clear cookie
    response.delete_cookie(key="access_token")
    
    # Redirect to home page
    return RedirectResponse(url="/", status_code=303)

# Profile routes
@router.get("/profile")
async def profile_page(
    request: Request,
    user: User = Depends(get_current_user),
    passkey_service: PasskeyService = Depends(get_passkey_service),
    db: Session = Depends(get_db)
):
    """Render the user profile page."""
    # Get user's passkeys
    passkeys = passkey_service.get_user_credentials(user.id, db)
    
    # Get active tokens
    tokens = db.query(JWTToken).filter(
        JWTToken.user_id == user.id,
        JWTToken.is_active == True
    ).all()
    
    # Get recent access logs
    access_logs = db.query(AuthAccessLog).filter(
        AuthAccessLog.user_id == user.id
    ).order_by(
        AuthAccessLog.timestamp.desc()
    ).limit(10).all()
    
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "title": "Your Profile",
            "user": user,
            "passkeys": passkeys,
            "tokens": tokens,
            "access_logs": access_logs
        }
    )

@router.post("/profile/update")
async def update_profile(
    request: Request,
    profile_data: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information."""
    # Check if username is being changed and is unique
    if profile_data.username and profile_data.username != user.username:
        existing_user = db.query(User).filter(User.username == profile_data.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = profile_data.username
    
    # Check if email is being changed and is unique
    if profile_data.email and profile_data.email != user.email:
        existing_user = db.query(User).filter(User.email == profile_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = profile_data.email
    
    # Check if phone number is being changed and is unique
    if profile_data.phone_number and profile_data.phone_number != user.phone_number:
        existing_user = db.query(User).filter(User.phone_number == profile_data.phone_number).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Phone number already exists")
        user.phone_number = profile_data.phone_number
    
    # Check if wallet address is being changed and is unique
    if profile_data.wallet_address and profile_data.wallet_address != user.wallet_address:
        existing_user = db.query(User).filter(User.wallet_address == profile_data.wallet_address).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Wallet address already exists")
        user.wallet_address = profile_data.wallet_address
    
    # Update display name
    if profile_data.display_name:
        user.display_name = profile_data.display_name
    
    # Log the profile update
    log_entry = AuthAccessLog(
        user_id=user.id,
        action="profile_update",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent")
    )
    db.add(log_entry)
    
    db.commit()
    
    return {"success": True, "message": "Profile updated successfully"}

# Passkey management routes
@router.post("/passkeys/add/begin")
async def start_add_passkey(
    request: Request,
    device_request: DeviceNameRequest,
    user: User = Depends(get_current_user),
    passkey_service: PasskeyService = Depends(get_passkey_service),
    db: Session = Depends(get_db)
):
    """Start the process of adding a new passkey to the user's account."""
    try:
        options = passkey_service.register_additional_passkey(
            user_id=user.id,
            request=request,
            db=db,
            device_name=device_request.device_name
        )
        return options
    except Exception as e:
        logger.error(f"Add passkey start failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/passkeys/add/complete")
async def complete_add_passkey(
    request: Request,
    credential_response: CredentialResponse,
    user: User = Depends(get_current_user),
    passkey_service: PasskeyService = Depends(get_passkey_service),
    db: Session = Depends(get_db)
):
    """Complete the process of adding a new passkey."""
    try:
        result = passkey_service.complete_additional_registration(
            request=request,
            db=db,
            credential_data=credential_response.credential
        )
        return {"success": True, "credential": result}
    except Exception as e:
        logger.error(f"Add passkey completion failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/passkeys/rename/{credential_id}")
async def rename_passkey(
    request: Request,
    credential_id: str,
    device_request: DeviceNameRequest,
    user: User = Depends(get_current_user),
    passkey_service: PasskeyService = Depends(get_passkey_service),
    db: Session = Depends(get_db)
):
    """Rename a passkey."""
    success = passkey_service.rename_credential(
        user_id=user.id,
        credential_id=credential_id,
        new_name=device_request.device_name,
        db=db,
        request=request
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    return {"success": True, "message": "Credential renamed successfully"}

@router.delete("/passkeys/{credential_id}")
async def remove_passkey(
    request: Request,
    credential_id: str,
    user: User = Depends(get_current_user),
    passkey_service: PasskeyService = Depends(get_passkey_service),
    db: Session = Depends(get_db)
):
    """Remove a passkey from the user's account."""
    try:
        success = passkey_service.remove_credential(
            user_id=user.id,
            credential_id=credential_id,
            db=db,
            request=request
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        return {"success": True, "message": "Credential removed successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Remove passkey failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Token management routes
@router.delete("/tokens/{token_id}")
async def remove_token(
    request: Request,
    token_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific token."""
    success = revoke_token(
        token_id=token_id,
        user_id=user.id,
        db=db,
        request=request
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Token not found")
    
    return {"success": True, "message": "Token revoked successfully"}

@router.post("/tokens/revoke-all")
async def revoke_all_tokens(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke all tokens for the user except the current one."""
    # Get current token
    token = request.cookies.get("access_token")
    current_token_id = None
    
    if token:
        from auth.jwt_service import validate_token
        token_data = validate_token(token, db, request, log_access=False)
        if token_data:
            current_token_id = token_data["token_id"]
    
    # Revoke all other tokens
    count = revoke_all_user_tokens(
        user_id=user.id,
        db=db,
        request=request,
        exclude_token_id=current_token_id
    )
    
    return {
        "success": True,
        "message": f"Successfully revoked {count} tokens",
        "count": count
    }