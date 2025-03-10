# plugins/twitter/models.py
"""
Database models for Twitter plugin
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base
from models import User, PostKey


class TwitterAccount(Base):
    __tablename__ = "twitter_accounts"
    
    twitter_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    twitter_cookie = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="twitter_accounts")
    sessions = relationship("UserSession", back_populates="twitter_account")


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