"""
Integration tests for Twitter cookie authentication routes
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Import models to ensure they're registered
from models import User
from plugins.twitter.models import TwitterAccount, TwitterOAuthCredential
from plugins.telegram.models import TelegramAccount, TelegramChannel

pytestmark = [pytest.mark.integration, pytest.mark.cookie_auth]


class TestTwitterCookieRoutes:
    """Test the Twitter cookie authentication routes"""
    
    def test_submit_cookie_success(self, client, monkeypatch, test_user, test_db):
        """Test submitting a cookie successfully"""
        # Mock the Twitter auth plugin
        with patch("plugin_manager.plugin_manager.create_authorization_plugin") as mock_create_auth:
            # Setup the mock plugin
            mock_auth = AsyncMock()
            mock_auth.validate_credentials = AsyncMock(return_value=True)
            mock_auth.get_user_identifier = AsyncMock(return_value="test-twitter-id")
            mock_auth.get_user_profile = AsyncMock(return_value={
                "username": "testuser",
                "name": "Test User",
                "profile_image_url": "https://example.com/avatar.jpg"
            })
            mock_auth.credentials_from_string = MagicMock(return_value={"cookie": "test"})
            mock_create_auth.return_value = mock_auth
            
            # Set up client session for the test user
            client.set_session({"user_id": test_user.id})
            
            # Make the request with JSON data
            response = client.post(
                "/twitter/auth/cookies",
                json={"cookie": "auth_token=abcdef; ct0=123456"},
                headers={"Content-Type": "application/json"}
            )
            
            # Verify we get a successful JSON response
            assert response.status_code == 201
            assert response.json()["status"] == "success"
            assert "account" in response.json()
            
            # Verify the mock was called correctly
            mock_create_auth.assert_called_with("twitter_cookie")
            mock_auth.validate_credentials.assert_called_once()
            mock_auth.get_user_identifier.assert_called_once()
            
            # Verify the account was created in the database
            account = test_db.query(TwitterAccount).filter_by(twitter_id="test-twitter-id").first()
            assert account is not None
            assert account.user_id == test_user.id
    
    def test_submit_cookie_no_auth(self, client):
        """Test submitting a cookie without authentication"""
        # Make the request without setting a session (unauthenticated)
        response = client.post(
            "/twitter/auth/cookies",
            json={"cookie": "auth_token=abcdef; ct0=123456"},
            headers={"Content-Type": "application/json"}
        )
        
        # Verify response indicates authentication is required
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]
    
    def test_submit_cookie_invalid(self, client, test_user):
        """Test submitting an invalid cookie"""
        # Mock the Twitter auth plugin to reject the cookie as invalid
        with patch("plugin_manager.plugin_manager.create_authorization_plugin") as mock_create_auth:
            # Setup the mock plugin with invalid credentials
            mock_auth = AsyncMock()
            mock_auth.validate_credentials = AsyncMock(return_value=False)
            mock_auth.get_user_profile = AsyncMock(return_value={})
            mock_auth.credentials_from_string = MagicMock(return_value={"cookie": "test"})
            mock_create_auth.return_value = mock_auth
            
            # Set up client session for the test user
            client.set_session({"user_id": test_user.id})
            
            # Make the request with JSON data to trigger API path
            response = client.post(
                "/twitter/auth/cookies",
                json={"cookie": "invalid-cookie"},
                headers={"Content-Type": "application/json"},
                allow_redirects=False
            )
            
            # With invalid credentials in JSON format, we get a 400 Bad Request
            assert response.status_code == 400
            
            # Verify the mock was called correctly
            mock_create_auth.assert_called_with("twitter_cookie")
            mock_auth.validate_credentials.assert_called_once()
    
    def test_submit_cookie_update_existing(self, client, test_user, test_twitter_account, test_db):
        """Test updating an existing Twitter account's cookie"""
        # Mock the Twitter auth plugin
        with patch("plugin_manager.plugin_manager.create_authorization_plugin") as mock_create_auth:
            # Setup the mock plugin
            mock_auth = AsyncMock()
            mock_auth.validate_credentials = AsyncMock(return_value=True)
            mock_auth.get_user_identifier = AsyncMock(return_value=test_twitter_account.twitter_id)
            mock_auth.get_user_profile = AsyncMock(return_value={
                "username": "testuser",
                "name": "Test User",
                "profile_image_url": "https://example.com/avatar.jpg"
            })
            mock_auth.credentials_from_string = MagicMock(return_value={"cookie": "test"})
            mock_create_auth.return_value = mock_auth
            
            # Record the original cookie
            original_cookie = test_twitter_account.twitter_cookie
            
            # Set up client session for the test user
            client.set_session({"user_id": test_user.id})
            
            # Make the request
            response = client.post(
                "/twitter/auth/cookies",
                json={"cookie": "auth_token=newtoken; ct0=newct0"},
                headers={"Content-Type": "application/json"}
            )
            
            # Verify we get a successful JSON response
            assert response.status_code == 201
            assert response.json()["status"] == "success"
            assert "account" in response.json()
            
            # Verify mocks were called
            mock_create_auth.assert_called_with("twitter_cookie")
            mock_auth.validate_credentials.assert_called_once()
            mock_auth.get_user_identifier.assert_called_once()
            
            # Refresh the account and verify it was updated
            test_db.refresh(test_twitter_account)
            assert test_twitter_account.twitter_cookie != original_cookie
            assert "newtoken" in test_twitter_account.twitter_cookie