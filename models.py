from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, create_engine, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import uuid

from database import Base

# Note: Plugin models will be imported from the plugins themselves

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=True)  # Now optional since passkey registration doesn't require username
    display_name = Column(String)
    email = Column(String, unique=True, nullable=True)
    phone_number = Column(String, unique=True, nullable=True)
    wallet_address = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credentials = relationship("WebAuthnCredential", back_populates="user")
    twitter_accounts = relationship("TwitterAccount", back_populates="user")
    telegram_accounts = relationship("TelegramAccount", back_populates="user")
    post_keys = relationship("PostKey", back_populates="user")
    access_tokens = relationship("JWTToken", back_populates="user")
    access_logs = relationship("AuthAccessLog", back_populates="user")

class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    credential_id = Column(String, unique=True, nullable=False)
    public_key = Column(String, nullable=False)  # Store as base64 encoded string
    sign_count = Column(Integer, default=0)
    transports = Column(String)  # JSON string of available transports
    device_name = Column(String, nullable=True)  # User-friendly name for the device
    attestation_type = Column(String, nullable=True)  # The type of attestation used
    aaguid = Column(String, nullable=True)  # Authenticator Attestation GUID
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)  # Allow disabling credentials without deleting
    
    # Relationship
    user = relationship("User", back_populates="credentials")


class PostKey(Base):
    __tablename__ = "post_keys"
    
    key_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))  # Changed from twitter_id to user_id
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    safety_level = Column(String, default="moderate")
    can_bypass_safety = Column(Boolean, default=False)
    
    # Relationship
    user = relationship("User", back_populates="post_keys")


class JWTToken(Base):
    __tablename__ = "jwt_tokens"
    
    token_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    policy = Column(String, nullable=False)  # Policy identifier: "passkey", "api", etc.
    scopes = Column(String, nullable=True)  # Optional space-separated scopes for API tokens
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_by_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="access_tokens")

class AuthAccessLog(Base):
    __tablename__ = "auth_access_logs"
    
    log_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_id = Column(String, ForeignKey("jwt_tokens.token_id"), nullable=True)
    credential_id = Column(String, ForeignKey("webauthn_credentials.id"), nullable=True)
    action = Column(String, nullable=False)  # "login", "register", "token_use", "logout", etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    success = Column(Boolean, default=True)
    details = Column(String, nullable=True)  # Additional details as JSON
    
    # Relationships
    user = relationship("User", back_populates="access_logs")
    token = relationship("JWTToken", foreign_keys=[token_id])
    credential = relationship("WebAuthnCredential", foreign_keys=[credential_id]) 