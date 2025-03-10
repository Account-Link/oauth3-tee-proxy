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
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credentials = relationship("WebAuthnCredential", back_populates="user")
    twitter_accounts = relationship("TwitterAccount", back_populates="user")
    telegram_accounts = relationship("TelegramAccount", back_populates="user")
    post_keys = relationship("PostKey", back_populates="user")
    oauth2_tokens = relationship("OAuth2Token", back_populates="user")

class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    credential_id = Column(String, unique=True, nullable=False)
    public_key = Column(String, nullable=False)  # Store as base64 encoded string
    sign_count = Column(Integer, default=0)
    transports = Column(String)  # JSON string of available transports
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    
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


class OAuth2Token(Base):
    __tablename__ = "oauth2_tokens"
    
    token_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    access_token = Column(String, unique=True, nullable=False)
    scopes = Column(String, nullable=False)  # Store as space-separated string: "telegram.post_any tweet.post"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    user_id = Column(String, ForeignKey("users.id"))
    
    # Relationship
    user = relationship("User", back_populates="oauth2_tokens") 