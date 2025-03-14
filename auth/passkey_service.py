"""
Passkey Authentication Service
=========================

This module provides a service for handling WebAuthn/passkey authentication.
It encapsulates all the WebAuthn logic and provides a clean interface for
registration and authentication of passkeys.

The service follows these principles:
- Complete separation of business logic from route handlers
- Comprehensive error handling and logging
- Support for multiple passkeys per user
- Detailed metadata about passkeys
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json
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

from database import get_db
from models import User, WebAuthnCredential, AuthAccessLog
from config import get_settings
from auth.jwt_service import create_token

# Get settings
settings = get_settings()

# Set up logger
logger = logging.getLogger(__name__)

class PasskeyService:
    """
    Service for handling WebAuthn/passkey authentication.
    
    This class encapsulates all functionality related to passkey registration
    and authentication, providing a clean interface for route handlers.
    """
    
    def __init__(self):
        """Initialize the passkey service with configuration."""
        self.rp_id = settings.WEBAUTHN_RP_ID
        self.rp_name = settings.WEBAUTHN_RP_NAME
        self.origin = settings.WEBAUTHN_ORIGIN
    
    def start_registration(
        self, 
        request: Request,
        db: Session,
        username: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Start passkey registration process.
        
        Args:
            request: The HTTP request
            db: Database session
            username: Optional username (can be set later in profile)
            display_name: Optional display name
            
        Returns:
            Tuple of (registration options, temp user ID)
        """
        # Check username if provided
        if username:
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already exists")
        
        # Generate temporary user ID
        temp_user_id = str(uuid.uuid4())
        
        # Generate registration options
        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=bytes(temp_user_id, "utf-8"),
            user_name=username or "user",
            user_display_name=display_name or username or "User",
            timeout=60000,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED
            ),
        )
        
        # Store challenge and registration data in session
        request.session["registration_challenge"] = bytes_to_base64url(options.challenge)
        request.session["registering_user_id"] = temp_user_id
        request.session["pending_registration"] = {
            "username": username,
            "display_name": display_name or username
        }
        
        return json.loads(options_to_json(options)), temp_user_id
    
    def complete_registration(
        self,
        request: Request,
        db: Session,
        credential_data: Dict[str, Any],
        device_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete passkey registration.
        
        Args:
            request: The HTTP request
            db: Database session
            credential_data: Credential data from client
            device_name: Optional name for this device
            
        Returns:
            Dict with user and session data
        """
        # Get stored challenge and registration data
        challenge = request.session.get("registration_challenge")
        temp_user_id = request.session.get("registering_user_id")
        pending_registration = request.session.get("pending_registration")
        
        if not challenge or not temp_user_id:
            raise HTTPException(status_code=400, detail="Registration session expired")
        
        try:
            # Verify the registration response
            attestation_response = AuthenticatorAttestationResponse(
                client_data_json=base64url_to_bytes(credential_data["response"]["clientDataJSON"]),
                attestation_object=base64url_to_bytes(credential_data["response"]["attestationObject"])
            )
            
            registration_credential = RegistrationCredential(
                id=credential_data["id"],
                raw_id=base64url_to_bytes(credential_data["rawId"]),
                response=attestation_response,
                type=credential_data["type"]
            )
            
            verification = verify_registration_response(
                credential=registration_credential,
                expected_challenge=base64url_to_bytes(challenge),
                expected_origin=self.origin,
                expected_rp_id=self.rp_id
            )
            
            # Create user
            username = pending_registration.get("username") if pending_registration else None
            display_name = pending_registration.get("display_name") if pending_registration else None
            
            user = User(
                username=username,
                display_name=display_name,
            )
            db.add(user)
            db.flush()  # Get the user ID
            
            # Extract attestation info
            attestation_type = None
            aaguid = None
            
            try:
                fmt = verification.fmt
                attestation_type = fmt
                if hasattr(verification, "aaguid") and verification.aaguid:
                    aaguid = verification.aaguid.hex()
            except Exception as e:
                logger.warning(f"Could not extract attestation info: {str(e)}")
            
            # Create credential
            credential = WebAuthnCredential(
                user_id=user.id,
                credential_id=bytes_to_base64url(verification.credential_id),
                public_key=bytes_to_base64url(verification.credential_public_key),
                sign_count=verification.sign_count,
                transports=json.dumps(credential_data.get("transports", [])),
                device_name=device_name or "Default passkey",
                attestation_type=attestation_type,
                aaguid=aaguid,
            )
            
            db.add(credential)
            
            # Log the registration
            log = AuthAccessLog(
                user_id=user.id,
                credential_id=credential.id,
                action="register",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                details=json.dumps({
                    "device_name": device_name or "Default passkey",
                    "transports": credential_data.get("transports", [])
                })
            )
            db.add(log)
            
            # Create JWT token
            token_data = create_token(
                user_id=user.id,
                policy="passkey",
                db=db,
                request=request
            )
            
            # Clear registration session data
            self._clear_registration_session(request)
            
            db.commit()
            
            return {
                "user_id": user.id,
                "token": token_data["token"],
                "token_id": token_data["token_id"],
                "expires_at": token_data["expires_at"]
            }
            
        except Exception as e:
            logger.error(f"Registration failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
    
    def start_authentication(
        self,
        request: Request,
        db: Session,
        username: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start passkey authentication.
        
        Args:
            request: The HTTP request
            db: Database session
            username: Optional username to authenticate
            user_id: Optional user ID to authenticate
            
        Returns:
            Dict with authentication options
        """
        # User can be identified by username or ID
        user = None
        
        if username:
            user = db.query(User).filter(User.username == username).first()
        elif user_id:
            user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        
        # Get user's credentials
        credentials = db.query(WebAuthnCredential).filter(
            WebAuthnCredential.user_id == user.id,
            WebAuthnCredential.is_active == True
        ).all()
        
        if not credentials:
            raise HTTPException(status_code=400, detail="No active credentials found for user")
        
        # Generate authentication options
        options = generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=[
                PublicKeyCredentialDescriptor(
                    type=PublicKeyCredentialType.PUBLIC_KEY,
                    id=base64url_to_bytes(cred.credential_id),
                    transports=[AuthenticatorTransport(t) for t in (json.loads(cred.transports) if cred.transports else [])]
                ) for cred in credentials
            ],
            user_verification=UserVerificationRequirement.PREFERRED,
            timeout=60000,
        )
        
        # Store challenge in session
        request.session["authentication_challenge"] = bytes_to_base64url(options.challenge)
        request.session["authenticating_user_id"] = user.id
        
        return options_to_json(options)
    
    def complete_authentication(
        self,
        request: Request,
        db: Session,
        credential_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete passkey authentication.
        
        Args:
            request: The HTTP request
            db: Database session
            credential_data: Credential data from client
            
        Returns:
            Dict with user and session data
        """
        # Get stored challenge and user ID
        challenge = request.session.get("authentication_challenge")
        user_id = request.session.get("authenticating_user_id")
        
        if not challenge or not user_id:
            raise HTTPException(status_code=400, detail="Authentication session expired")
        
        try:
            # Get credential
            credential_id = credential_data.get("id")
            if not credential_id:
                raise HTTPException(status_code=400, detail="No credential ID provided")
            
            credential = db.query(WebAuthnCredential).filter(
                WebAuthnCredential.credential_id == credential_id,
                WebAuthnCredential.user_id == user_id,
                WebAuthnCredential.is_active == True
            ).first()
            
            if not credential:
                raise HTTPException(status_code=400, detail="Credential not found or inactive")
            
            # Verify the authentication response
            assertion_response = AuthenticatorAssertionResponse(
                client_data_json=base64url_to_bytes(credential_data["response"]["clientDataJSON"]),
                authenticator_data=base64url_to_bytes(credential_data["response"]["authenticatorData"]),
                signature=base64url_to_bytes(credential_data["response"]["signature"]),
                user_handle=base64url_to_bytes(credential_data["response"]["userHandle"]) if "userHandle" in credential_data["response"] else None
            )
            
            authentication_credential = AuthenticationCredential(
                id=credential_data["id"],
                raw_id=base64url_to_bytes(credential_data["rawId"]),
                response=assertion_response,
                type=credential_data["type"]
            )
            
            verification = verify_authentication_response(
                credential=authentication_credential,
                expected_challenge=base64url_to_bytes(challenge),
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
                credential_public_key=base64url_to_bytes(credential.public_key),
                credential_current_sign_count=credential.sign_count
            )
            
            # Update credential sign count and last used timestamp
            credential.sign_count = verification.new_sign_count
            credential.last_used_at = datetime.utcnow()
            
            # Create JWT token
            token_data = create_token(
                user_id=user_id,
                policy="passkey",
                db=db,
                request=request
            )
            
            # Log the authentication
            log = AuthAccessLog(
                user_id=user_id,
                credential_id=credential.id,
                token_id=token_data["token_id"],
                action="login",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            db.add(log)
            
            # Clear authentication session data
            self._clear_authentication_session(request)
            
            db.commit()
            
            # Get user for return data
            user = db.query(User).filter(User.id == user_id).first()
            
            return {
                "user_id": user_id,
                "username": user.username if user else None,
                "token": token_data["token"],
                "token_id": token_data["token_id"],
                "expires_at": token_data["expires_at"]
            }
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
    
    def get_user_credentials(
        self,
        user_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Get all passkeys for a user.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            List of credential data
        """
        # Get all credentials
        credentials = db.query(WebAuthnCredential).filter(
            WebAuthnCredential.user_id == user_id
        ).all()
        
        result = []
        for cred in credentials:
            # Get last used info
            last_used = None
            if cred.last_used_at:
                last_used = cred.last_used_at.isoformat()
            
            # Parse transports
            transports = []
            if cred.transports:
                try:
                    transports = json.loads(cred.transports)
                except:
                    pass
            
            result.append({
                "id": cred.id,
                "device_name": cred.device_name or "Unknown device",
                "created_at": cred.created_at.isoformat(),
                "last_used_at": last_used,
                "is_active": cred.is_active,
                "transports": transports,
                "attestation_type": cred.attestation_type
            })
        
        return result
    
    def register_additional_passkey(
        self,
        user_id: str,
        request: Request,
        db: Session,
        device_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register an additional passkey for an existing user.
        
        Args:
            user_id: ID of existing user
            request: HTTP request
            db: Database session
            device_name: Optional device name
            
        Returns:
            Dict with registration options
        """
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate registration options
        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=bytes(user.id, "utf-8"),
            user_name=user.username or "user",
            user_display_name=user.display_name or user.username or "User",
            timeout=60000,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED
            ),
        )
        
        # Store challenge and data in session
        request.session["registration_challenge"] = bytes_to_base64url(options.challenge)
        request.session["registering_user_id"] = user.id
        request.session["pending_registration"] = {
            "additional_key": True,
            "device_name": device_name
        }
        
        return json.loads(options_to_json(options))
    
    def complete_additional_registration(
        self,
        request: Request,
        db: Session,
        credential_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete registration of an additional passkey.
        
        Args:
            request: HTTP request
            db: Database session
            credential_data: Credential data from client
            
        Returns:
            Dict with credential info
        """
        # Get stored challenge and registration data
        challenge = request.session.get("registration_challenge")
        user_id = request.session.get("registering_user_id")
        pending_data = request.session.get("pending_registration")
        
        if not challenge or not user_id or not pending_data or not pending_data.get("additional_key"):
            raise HTTPException(status_code=400, detail="Registration session expired or invalid")
        
        try:
            # Get device name
            device_name = pending_data.get("device_name") or "Additional passkey"
            
            # Verify the registration response
            attestation_response = AuthenticatorAttestationResponse(
                client_data_json=base64url_to_bytes(credential_data["response"]["clientDataJSON"]),
                attestation_object=base64url_to_bytes(credential_data["response"]["attestationObject"])
            )
            
            registration_credential = RegistrationCredential(
                id=credential_data["id"],
                raw_id=base64url_to_bytes(credential_data["rawId"]),
                response=attestation_response,
                type=credential_data["type"]
            )
            
            verification = verify_registration_response(
                credential=registration_credential,
                expected_challenge=base64url_to_bytes(challenge),
                expected_origin=self.origin,
                expected_rp_id=self.rp_id
            )
            
            # Extract attestation info
            attestation_type = None
            aaguid = None
            
            try:
                fmt = verification.fmt
                attestation_type = fmt
                if hasattr(verification, "aaguid") and verification.aaguid:
                    aaguid = verification.aaguid.hex()
            except Exception as e:
                logger.warning(f"Could not extract attestation info: {str(e)}")
            
            # Create credential
            credential = WebAuthnCredential(
                user_id=user_id,
                credential_id=bytes_to_base64url(verification.credential_id),
                public_key=bytes_to_base64url(verification.credential_public_key),
                sign_count=verification.sign_count,
                transports=json.dumps(credential_data.get("transports", [])),
                device_name=device_name,
                attestation_type=attestation_type,
                aaguid=aaguid,
            )
            
            db.add(credential)
            
            # Log the registration
            log = AuthAccessLog(
                user_id=user_id,
                credential_id=credential.id,
                action="register_additional",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                details=json.dumps({
                    "device_name": device_name,
                    "transports": credential_data.get("transports", [])
                })
            )
            db.add(log)
            
            # Clear registration session data
            self._clear_registration_session(request)
            
            db.commit()
            
            return {
                "credential_id": credential.id,
                "device_name": device_name,
                "created_at": credential.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Additional registration failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
    
    def remove_credential(
        self,
        user_id: str,
        credential_id: str,
        db: Session,
        request: Optional[Request] = None
    ) -> bool:
        """
        Remove a passkey from a user account.
        
        Args:
            user_id: User ID
            credential_id: Credential ID to remove
            db: Database session
            request: Optional request for logging
            
        Returns:
            True if successful, False otherwise
        """
        # Get credential
        credential = db.query(WebAuthnCredential).filter(
            WebAuthnCredential.id == credential_id,
            WebAuthnCredential.user_id == user_id
        ).first()
        
        if not credential:
            return False
        
        # Check if this is the only credential
        cred_count = db.query(WebAuthnCredential).filter(
            WebAuthnCredential.user_id == user_id,
            WebAuthnCredential.is_active == True
        ).count()
        
        if cred_count <= 1:
            raise HTTPException(
                status_code=400, 
                detail="Cannot remove the only active credential. Add another passkey first."
            )
        
        # Deactivate credential instead of deleting
        credential.is_active = False
        
        # Log the removal
        if request:
            log = AuthAccessLog(
                user_id=user_id,
                credential_id=credential_id,
                action="remove_credential",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                details=f"Removed credential: {credential.device_name}"
            )
            db.add(log)
        
        db.commit()
        
        return True
    
    def rename_credential(
        self,
        user_id: str,
        credential_id: str,
        new_name: str,
        db: Session,
        request: Optional[Request] = None
    ) -> bool:
        """
        Rename a passkey.
        
        Args:
            user_id: User ID
            credential_id: Credential ID to rename
            new_name: New device name
            db: Database session
            request: Optional request for logging
            
        Returns:
            True if successful, False otherwise
        """
        # Get credential
        credential = db.query(WebAuthnCredential).filter(
            WebAuthnCredential.id == credential_id,
            WebAuthnCredential.user_id == user_id
        ).first()
        
        if not credential:
            return False
        
        # Update name
        old_name = credential.device_name or "Unknown device"
        credential.device_name = new_name
        
        # Log the rename
        if request:
            log = AuthAccessLog(
                user_id=user_id,
                credential_id=credential_id,
                action="rename_credential",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                details=f"Renamed from '{old_name}' to '{new_name}'"
            )
            db.add(log)
        
        db.commit()
        
        return True
    
    def _clear_registration_session(self, request: Request) -> None:
        """Clear registration session data."""
        request.session.pop("registration_challenge", None)
        request.session.pop("registering_user_id", None)
        request.session.pop("pending_registration", None)
    
    def _clear_authentication_session(self, request: Request) -> None:
        """Clear authentication session data."""
        request.session.pop("authentication_challenge", None)
        request.session.pop("authenticating_user_id", None)

# Singleton instance and getter function for dependency injection
_passkey_service = None

def get_passkey_service() -> PasskeyService:
    """Get or create the passkey service singleton."""
    global _passkey_service
    if _passkey_service is None:
        _passkey_service = PasskeyService()
    return _passkey_service