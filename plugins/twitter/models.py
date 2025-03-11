# plugins/twitter/models.py
"""
Database models for Twitter plugin

This module defines the database models used by the Twitter plugin, with clear
separation between authorization-related and resource-related models.

The models are organized as follows:
- Authorization models: Store credentials and authentication information
- Resource models: Store information about resource access and usage logs
- Policy models: Store policy configurations for access control
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Table, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import json

from database import Base
from models import User, PostKey, OAuth2Token

#
# Authorization Server Models
#

class TwitterAccount(Base):
    """
    Represents a Twitter account linked to a user through one or more authorization methods.
    
    This is the central model that connects a user to their Twitter identity, with relationships
    to specific authorization methods (like cookies or OAuth).
    """
    __tablename__ = "twitter_accounts"
    
    twitter_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Flag to indicate if the account can be used for login
    can_login = Column(Boolean, default=True)
    
    # Authentication methods
    twitter_cookie = Column(String, nullable=True)  # Legacy field for cookie authentication
    
    # Twitter user information
    username = Column(String, nullable=True)  # Twitter username/handle
    display_name = Column(String, nullable=True)  # User's display name
    profile_image_url = Column(String, nullable=True)  # URL to profile image
    
    # Access policy - stores the policy in JSON format
    policy_json = Column(String, nullable=True, default=None)
    
    # Relationships
    user = relationship("User", back_populates="twitter_accounts")
    sessions = relationship("UserSession", back_populates="twitter_account")
    oauth_credentials = relationship("TwitterOAuthCredential", back_populates="twitter_account")
    
    @property
    def policy(self):
        """
        Get the policy as a dictionary.
        
        Returns:
            dict: The policy as a dictionary, or the default policy if none is set
        """
        if not self.policy_json:
            # Import here to avoid circular imports
            from plugins.twitter.policy import TwitterPolicy
            return TwitterPolicy.get_default_policy().to_dict()
        
        try:
            return json.loads(self.policy_json)
        except json.JSONDecodeError:
            # If the JSON is invalid, return the default policy
            from plugins.twitter.policy import TwitterPolicy
            return TwitterPolicy.get_default_policy().to_dict()
    
    @policy.setter
    def policy(self, policy_dict):
        """
        Set the policy from a dictionary.
        
        Args:
            policy_dict (dict): The policy as a dictionary
        """
        if policy_dict is None:
            self.policy_json = None
        else:
            self.policy_json = json.dumps(policy_dict)


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
# OAuth Models
#

class TwitterOAuthCredential(Base):
    """
    Represents OAuth credentials for a Twitter account.
    
    This model stores the OAuth tokens and related information for Twitter
    accounts that are authenticated using the OAuth flow.
    """
    __tablename__ = "twitter_oauth_credentials"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    twitter_account_id = Column(String, ForeignKey("twitter_accounts.twitter_id"))
    oauth_token = Column(String, nullable=False)
    oauth_token_secret = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    twitter_account = relationship("TwitterAccount", back_populates="oauth_credentials")


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