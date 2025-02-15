from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()

class TwitterAccount(Base):
    __tablename__ = "twitter_accounts"
    
    twitter_id = Column(String, primary_key=True)
    twitter_cookie = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    post_keys = relationship("PostKey", back_populates="twitter_account")
    sessions = relationship("UserSession", back_populates="twitter_account")

class PostKey(Base):
    __tablename__ = "post_keys"
    
    key_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    twitter_id = Column(String, ForeignKey("twitter_accounts.twitter_id"))
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    safety_level = Column(String, default="moderate")
    can_bypass_safety = Column(Boolean, default=False)
    
    # Relationship
    twitter_account = relationship("TwitterAccount", back_populates="post_keys")

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
    post_key_id = Column(String, ForeignKey("post_keys.key_id"))
    tweet_text = Column(String)
    safety_check_result = Column(Boolean)
    safety_check_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    post_key = relationship("PostKey") 