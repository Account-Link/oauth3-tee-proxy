# plugins/twitter/models.py
"""
Database models for Twitter plugin

This module defines the database models used by the Twitter plugin, with clear
separation between authorization-related and resource-related models.

The models are organized as follows:
- Authorization models: Store credentials and authentication information
- Resource models: Store information about resource access and usage logs
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base
from models import User, PostKey

#
# Authorization Server Models
#

class TwitterAccount(Base):
    """
    Represents a Twitter account linked to a user through one or more authorization methods.
    
    This is the central model that connects a user to their Twitter identity, with relationships
    to specific authorization methods (like cookies).
    """
    __tablename__ = "twitter_accounts"
    
    twitter_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Authentication methods
    twitter_cookie = Column(String, nullable=True)  # Legacy field for cookie authentication
    
    # Relationships
    user = relationship("User", back_populates="twitter_accounts")
    sessions = relationship("UserSession", back_populates="twitter_account")


class UserSession(Base):
    """
    Represents an active session for a Twitter account.
    
    This model tracks active user sessions and their expiration times.
    """
    __tablename__ = "user_sessions"
    
    session_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    twitter_id = Column(String, ForeignKey("twitter_accounts.twitter_id"))
    session_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    twitter_account = relationship("TwitterAccount", back_populates="sessions")


#
# Resource Server Models
#

class TweetLog(Base):
    """
    Logs tweets posted through the system.
    
    This model tracks tweets posted through the system, including the text,
    the resulting tweet ID, and safety check information.
    """
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