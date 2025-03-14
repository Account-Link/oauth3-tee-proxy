from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, create_engine, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import uuid

from database import Base

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

class TwitterAccount(Base):
    __tablename__ = "twitter_accounts"
    
    twitter_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    twitter_cookie = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    can_login = Column(Boolean, default=True)  # Whether this Twitter account can be used for login
    
    # Relationships
    user = relationship("User", back_populates="twitter_accounts")
    sessions = relationship("UserSession", back_populates="twitter_account")
    oauth_credentials = relationship("TwitterOAuthCredential", back_populates="twitter_account")

class TwitterOAuthCredential(Base):
    __tablename__ = "twitter_oauth_credentials"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    twitter_account_id = Column(String, ForeignKey("twitter_accounts.twitter_id"))
    oauth_token = Column(String, nullable=False)
    oauth_token_secret = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    twitter_account = relationship("TwitterAccount", back_populates="oauth_credentials")

class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    phone_number = Column(String, nullable=False)
    session_string = Column(String, nullable=True)  # Store Telethon session string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="telegram_accounts")
    channels = relationship("TelegramChannel", back_populates="telegram_account")

class TelegramChannel(Base):
    __tablename__ = "telegram_channels"
    
    id = Column(String, primary_key=True)  # Telegram's channel ID
    telegram_account_id = Column(String, ForeignKey("telegram_accounts.id"))
    name = Column(String, nullable=False)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    telegram_account = relationship("TelegramAccount", back_populates="channels")

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

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    session_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    twitter_id = Column(String, ForeignKey("twitter_accounts.twitter_id"))
    session_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    twitter_account = relationship("TwitterAccount", back_populates="sessions")

class TweetLog(Base):
    __tablename__ = "tweet_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_key_id = Column(String, ForeignKey("post_keys.key_id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    tweet_text = Column(String, nullable=False)
    tweet_id = Column(String, nullable=True)
    safety_check_result = Column(Boolean)
    safety_check_message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post_key = relationship("PostKey")
    user = relationship("User")

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

class OAuth2Request(Base):
    __tablename__ = "oauth2_requests"
    
    request_id = Column(String, primary_key=True)
    callback_url = Column(String, nullable=False)
    scope = Column(String, nullable=False)
    state = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    def __init__(self, request_id, callback_url, scope, state, created_at, expires_at):
        self.request_id = request_id
        self.callback_url = callback_url
        self.scope = scope
        self.state = state
        self.created_at = created_at
        self.expires_at = expires_at 