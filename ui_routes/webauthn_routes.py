from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers import (
    bytes_to_base64url,
    base64url_to_bytes,
)
from webauthn.helpers.structs import (
    RegistrationCredential,
    AuthenticationCredential,
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    AuthenticatorAttestationResponse,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    AuthenticatorTransport,
    AuthenticatorAssertionResponse,
)
import json
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import uuid
import traceback
import sys

from models import User, WebAuthnCredential
from config import get_settings
from database import get_db

router = APIRouter(prefix="/webauthn", tags=["UI:WebAuthn"])
settings = get_settings()

# Configuration
RP_ID = settings.WEBAUTHN_RP_ID
RP_NAME = settings.WEBAUTHN_RP_NAME
ORIGIN = settings.WEBAUTHN_ORIGIN

class RegistrationSession:
    """Handles temporary registration data in the session"""
    def __init__(self, request: Request):
        self.session = request.session
    
    def store_challenge(self, challenge: bytes, user_id: str):
        """Store registration challenge and user ID"""
        self.session["registration_challenge"] = bytes_to_base64url(challenge)
        self.session["registering_user_id"] = user_id
    
    def get_challenge(self) -> Optional[bytes]:
        """Get stored challenge or None if not found"""
        challenge = self.session.get("registration_challenge")
        return base64url_to_bytes(challenge) if challenge else None
    
    def get_user_id(self) -> Optional[str]:
        """Get stored user ID or None if not found"""
        return self.session.get("registering_user_id")
    
    def clear(self):
        """Clear registration data from session"""
        self.session.pop("registration_challenge", None)
        self.session.pop("registering_user_id", None)
    
    def create_user_session(self, user_id: str):
        """Create the main user session after successful registration"""
        session_token = str(uuid.uuid4())
        self.session.update({
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": (datetime.utcnow() + timedelta(hours=settings.SESSION_EXPIRY_HOURS)).isoformat()
        })

class AuthenticationSession:
    """Handles temporary authentication data in the session"""
    def __init__(self, request: Request):
        self.session = request.session
    
    def store_challenge(self, challenge: bytes, user_id: str):
        """Store authentication challenge and user ID"""
        self.session["authentication_challenge"] = bytes_to_base64url(challenge)
        self.session["authenticating_user_id"] = user_id
    
    def get_challenge(self) -> Optional[bytes]:
        """Get stored challenge or None if not found"""
        challenge = self.session.get("authentication_challenge")
        return base64url_to_bytes(challenge) if challenge else None
    
    def get_user_id(self) -> Optional[str]:
        """Get stored user ID or None if not found"""
        return self.session.get("authenticating_user_id")
    
    def clear(self):
        """Clear authentication data from session"""
        self.session.pop("authentication_challenge", None)
        self.session.pop("authenticating_user_id", None)
    
    def create_user_session(self, user_id: str):
        """Create the main user session after successful authentication"""
        session_token = str(uuid.uuid4())
        self.session.update({
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": (datetime.utcnow() + timedelta(hours=settings.SESSION_EXPIRY_HOURS)).isoformat()
        })

def get_registration_session(request: Request) -> RegistrationSession:
    return RegistrationSession(request)

def get_authentication_session(request: Request) -> AuthenticationSession:
    return AuthenticationSession(request)

class RegistrationRequest(BaseModel):
    username: str
    display_name: Optional[str] = None

class RegistrationResponse(BaseModel):
    credential: dict
    client_data: str

class AuthenticationRequest(BaseModel):
    username: str

class AuthenticationResponse(BaseModel):
    credential: dict
    client_data: str

@router.post("/register/begin")
async def start_registration(
    request: RegistrationRequest,
    reg_session: RegistrationSession = Depends(get_registration_session),
    db: Session = Depends(get_db)
):
    """Begin the WebAuthn registration process by generating registration options."""
    # Check if username is available
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Generate a temporary user ID
    temp_user_id = str(uuid.uuid4())

    # Generate registration options
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=bytes(temp_user_id, "utf-8"),
        user_name=request.username,
        user_display_name=request.display_name or request.username,
        timeout=60000,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED
        ),
    )
    
    # Store challenge and registration data in session
    reg_session.store_challenge(options.challenge, temp_user_id)
    reg_session.session["pending_registration"] = {
        "username": request.username,
        "display_name": request.display_name or request.username
    }
    
    return json.loads(options_to_json(options))

@router.post("/register/complete")
async def complete_registration(
    response: RegistrationResponse,
    reg_session: RegistrationSession = Depends(get_registration_session),
    db: Session = Depends(get_db)
):
    """Complete the WebAuthn registration process by verifying the authenticator response."""
    expected_challenge = reg_session.get_challenge()
    temp_user_id = reg_session.get_user_id()
    pending_registration = reg_session.session.get("pending_registration")
    
    if not expected_challenge or not temp_user_id or not pending_registration:
        raise HTTPException(status_code=400, detail="Registration session expired")
    
    try:
        # Verify the registration response first
        attestation_response = AuthenticatorAttestationResponse(
            client_data_json=base64url_to_bytes(response.credential["response"]["clientDataJSON"]),
            attestation_object=base64url_to_bytes(response.credential["response"]["attestationObject"])
        )
        
        registration_credential = RegistrationCredential(
            id=response.credential["id"],
            raw_id=base64url_to_bytes(response.credential["rawId"]),
            response=attestation_response,
            type=response.credential["type"]
        )
        
        verification = verify_registration_response(
            credential=registration_credential,
            expected_challenge=expected_challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID
        )

        # Only create the user after successful verification
        user = User(
            username=pending_registration["username"],
            display_name=pending_registration["display_name"],
        )
        db.add(user)
        db.flush()  # Get the user ID

        # Create WebAuthn credential
        credential = WebAuthnCredential(
            user_id=user.id,
            credential_id=bytes_to_base64url(verification.credential_id),
            public_key=bytes_to_base64url(verification.credential_public_key),
            sign_count=verification.sign_count,
            transports=json.dumps(response.credential.get("transports", [])),
        )
        
        db.add(credential)
        db.commit()
        
        # Clear registration session and create user session
        reg_session.clear()
        reg_session.create_user_session(user.id)
        
        return {"status": "success", "user_id": user.id, "redirect": "/auth/profile"}
        
    except Exception as e:
        print("Registration failed with error:", str(e))
        print("Error type:", type(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login/begin")
async def start_authentication(
    request: AuthenticationRequest,
    auth_session: AuthenticationSession = Depends(get_authentication_session),
    db: Session = Depends(get_db)
):
    """Begin the WebAuthn authentication process by generating authentication options."""
    try:
        # Find user by username
        user = db.query(User).filter(User.username == request.username).first()
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        
        # Get user's credentials
        credentials = db.query(WebAuthnCredential).filter(
            WebAuthnCredential.user_id == user.id
        ).all()
        
        if not credentials:
            raise HTTPException(status_code=400, detail="No credentials found for user")
        
        # Generate authentication options
        options = generate_authentication_options(
            rp_id=RP_ID,
            allow_credentials=[
                PublicKeyCredentialDescriptor(
                    type=PublicKeyCredentialType.PUBLIC_KEY,
                    id=base64url_to_bytes(cred.credential_id),
                    transports=[AuthenticatorTransport(t) for t in json.loads(cred.transports)] if cred.transports else None
                ) for cred in credentials
            ],
            user_verification=UserVerificationRequirement.PREFERRED,
            timeout=60000,
        )
        
        # Store challenge in authentication session
        auth_session.store_challenge(options.challenge, user.id)
        return options_to_json(options)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login/complete")
async def complete_authentication(
    response: AuthenticationResponse,
    auth_session: AuthenticationSession = Depends(get_authentication_session),
    db: Session = Depends(get_db)
):
    """Complete the WebAuthn authentication process by verifying the authenticator response."""
    try:
        expected_challenge = auth_session.get_challenge()
        user_id = auth_session.get_user_id()
        
        if not expected_challenge or not user_id:
            raise HTTPException(status_code=400, detail="Authentication session expired")
        
        # Get user and credential
        credential_id = response.credential.get("id")
        if not credential_id:
            raise HTTPException(status_code=400, detail="No credential ID provided")
        
        stored_credential = db.query(WebAuthnCredential).filter(
            WebAuthnCredential.credential_id == credential_id,
            WebAuthnCredential.user_id == user_id
        ).first()
        
        if not stored_credential:
            raise HTTPException(status_code=400, detail="Credential not found")

        # Construct AuthenticationCredential object
        assertion_response = AuthenticatorAssertionResponse(
            client_data_json=base64url_to_bytes(response.credential["response"]["clientDataJSON"]),
            authenticator_data=base64url_to_bytes(response.credential["response"]["authenticatorData"]),
            signature=base64url_to_bytes(response.credential["response"]["signature"]),
            user_handle=base64url_to_bytes(response.credential["response"]["userHandle"]) if "userHandle" in response.credential["response"] else None
        )

        authentication_credential = AuthenticationCredential(
            id=response.credential["id"],
            raw_id=base64url_to_bytes(response.credential["rawId"]),
            response=assertion_response,
            type=response.credential["type"]
        )
        
        verification = verify_authentication_response(
            credential=authentication_credential,
            expected_challenge=expected_challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=base64url_to_bytes(stored_credential.public_key),
            credential_current_sign_count=stored_credential.sign_count
        )
        
        # Update credential sign count and create session
        stored_credential.sign_count = verification.new_sign_count
        stored_credential.last_used_at = datetime.utcnow()
        
        auth_session.clear()
        auth_session.create_user_session(user_id)
        
        db.commit()
        return {"status": "success", "user_id": user_id, "redirect": "/auth/profile"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))