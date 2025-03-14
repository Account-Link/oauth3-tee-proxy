"""
Test JWT Token Service
=====================

This module contains tests for the JWT token service functionality.
"""

import unittest
import pytest
from datetime import datetime, timedelta
import jwt

# Import User and JWTToken directly from database module for testing
# This avoids SQLAlchemy relationship errors with plugin models
from database import get_db, Base
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean

# Import directly from models.py instead of redefining
from models import User, JWTToken

# Import the functions to test
from auth.jwt_service import create_token, validate_token, revoke_token, revoke_all_user_tokens

class TestJWTService:
    """Test cases for JWT token service."""
    
    @pytest.fixture
    def db_session(self):
        """Get a database session for tests."""
        return next(get_db())
    
    @pytest.fixture
    def test_user(self, db_session):
        """Create a test user for token operations."""
        # Check if test user already exists
        existing_user = db_session.query(User).filter(User.username == "test_jwt_user").first()
        if existing_user:
            return existing_user
            
        # Create test user
        user = User(
            username="test_jwt_user",
            display_name="Test JWT User"
        )
        db_session.add(user)
        db_session.commit()
        
        yield user
        
        # Cleanup not needed - we'll keep the test user
    
    def test_create_token(self, db_session, test_user):
        """Test creating a JWT token."""
        # Create token
        token_data = create_token(
            user_id=test_user.id,
            policy="test",
            scopes=["test.read", "test.write"],
            db=db_session
        )
        
        # Verify token was created
        assert "token" in token_data
        assert "token_id" in token_data
        assert "expires_at" in token_data
        assert token_data["policy"] == "test"
        
        # Verify token in database
        db_token = db_session.query(JWTToken).filter(
            JWTToken.token_id == token_data["token_id"]
        ).first()
        
        assert db_token is not None
        assert db_token.user_id == test_user.id
        assert db_token.policy == "test"
        assert "test.read" in db_token.scopes
        assert "test.write" in db_token.scopes
        assert db_token.is_active is True
        
        # Check that the token expires in approximately 2 hours
        now = datetime.utcnow()
        assert db_token.expires_at > now + timedelta(hours=1, minutes=55)
        assert db_token.expires_at < now + timedelta(hours=2, minutes=5)
        
        # Clean up
        db_session.delete(db_token)
        db_session.commit()
    
    def test_validate_token(self, db_session, test_user):
        """Test validating a JWT token."""
        # Create token
        token_data = create_token(
            user_id=test_user.id,
            policy="test",
            scopes=["test.read"],
            db=db_session
        )
        
        # Validate token
        result = validate_token(
            token=token_data["token"],
            db=db_session,
            log_access=False
        )
        
        # Verify validation result
        assert result is not None
        assert result["user_id"] == test_user.id
        assert result["policy"] == "test"
        assert "test.read" in result["scopes"]
        assert result["user"] is not None
        assert result["user"].id == test_user.id
        
        # Clean up
        db_token = db_session.query(JWTToken).filter(
            JWTToken.token_id == token_data["token_id"]
        ).first()
        db_session.delete(db_token)
        db_session.commit()
    
    def test_revoke_token(self, db_session, test_user):
        """Test revoking a JWT token."""
        # Create token
        token_data = create_token(
            user_id=test_user.id,
            policy="test",
            db=db_session
        )
        
        # Verify token is active
        db_token = db_session.query(JWTToken).filter(
            JWTToken.token_id == token_data["token_id"]
        ).first()
        assert db_token.is_active is True
        
        # Revoke token
        result = revoke_token(
            token_id=token_data["token_id"],
            user_id=test_user.id,
            db=db_session
        )
        
        # Verify token was revoked
        assert result is True
        
        # Verify token in database
        db_token = db_session.query(JWTToken).filter(
            JWTToken.token_id == token_data["token_id"]
        ).first()
        assert db_token.is_active is False
        assert db_token.revoked_at is not None
        
        # Verify token validation fails
        result = validate_token(
            token=token_data["token"],
            db=db_session,
            log_access=False
        )
        assert result is None
        
        # Clean up
        db_session.delete(db_token)
        db_session.commit()
    
    def test_revoke_all_user_tokens(self, db_session, test_user):
        """Test revoking all JWT tokens for a user."""
        # Create multiple tokens
        token1 = create_token(user_id=test_user.id, policy="test1", db=db_session)
        token2 = create_token(user_id=test_user.id, policy="test2", db=db_session)
        token3 = create_token(user_id=test_user.id, policy="test3", db=db_session)
        
        # Verify tokens are active
        tokens = db_session.query(JWTToken).filter(
            JWTToken.user_id == test_user.id,
            JWTToken.is_active == True
        ).all()
        assert len(tokens) >= 3
        
        # Revoke all but one token
        exclude_token_id = token1["token_id"]
        count = revoke_all_user_tokens(
            user_id=test_user.id,
            db=db_session,
            exclude_token_id=exclude_token_id
        )
        
        # Verify tokens were revoked
        assert count >= 2
        
        # Verify only the excluded token is still active
        active_tokens = db_session.query(JWTToken).filter(
            JWTToken.user_id == test_user.id,
            JWTToken.is_active == True
        ).all()
        assert len(active_tokens) == 1
        assert active_tokens[0].token_id == exclude_token_id
        
        # Clean up
        for token in db_session.query(JWTToken).filter(JWTToken.user_id == test_user.id).all():
            db_session.delete(token)
        db_session.commit()
    
    def test_invalid_token(self, db_session, test_user):
        """Test validation with invalid token."""
        # Invalid token format
        result = validate_token(
            token="invalid-token",
            db=db_session
        )
        assert result is None
        
        # Valid format but wrong signature
        payload = {
            "sub": test_user.id,
            "policy": "test",
            "jti": "fake-token-id",
            "exp": (datetime.utcnow() + timedelta(hours=2)).timestamp()
        }
        fake_token = jwt.encode(
            payload,
            "wrong-secret-key",
            algorithm="HS256"
        )
        
        result = validate_token(
            token=fake_token,
            db=db_session
        )
        assert result is None