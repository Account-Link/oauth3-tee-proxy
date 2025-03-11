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
    
    def test_submit_cookie_success(self, client, monkeypatch, test_user):
        """Test submitting a cookie successfully"""
        # Mock the Twitter auth plugin
        with patch("plugin_manager.plugin_manager.create_authorization_plugin") as mock_create_auth:
            # Setup the mock plugin
            mock_auth = AsyncMock()
            mock_auth.validate_credentials = AsyncMock(return_value=True)
            mock_auth.get_user_identifier = AsyncMock(return_value="test-twitter-id")
            mock_auth.credentials_from_string = MagicMock(return_value={"cookie": "test"})
            mock_create_auth.return_value = mock_auth
            
            # Set up client session for the test user
            client.set_session({"user_id": test_user.id})
            
            # Make the request
            response = client.post(
                "/twitter/cookie",
                data={"twitter_cookie": "auth_token=abcdef; ct0=123456"}
            )
            
            # Verify response
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            assert response.json()["message"] == "Twitter account linked successfully"
            
            # Verify the mock was called correctly
            mock_create_auth.assert_called_with("twitter_cookie")
            mock_auth.validate_credentials.assert_called_once()
            mock_auth.get_user_identifier.assert_called_once()
    
    def test_submit_cookie_no_auth(self, client):
        """Test submitting a cookie without authentication"""
        # Make the request without setting a session (unauthenticated)
        response = client.post(
            "/twitter/cookie",
            data={"twitter_cookie": "auth_token=abcdef; ct0=123456"}
        )
        
        # Verify response indicates authentication is required
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    def test_submit_cookie_invalid(self, client, test_user):
        """Test submitting an invalid cookie"""
        # Mock the Twitter auth plugin to reject the cookie as invalid
        with patch("plugin_manager.plugin_manager.create_authorization_plugin") as mock_create_auth:
            # Setup the mock plugin with invalid credentials
            mock_auth = AsyncMock()
            mock_auth.validate_credentials = AsyncMock(return_value=False)
            mock_auth.credentials_from_string = MagicMock(return_value={"cookie": "test"})
            mock_create_auth.return_value = mock_auth
            
            # Set up client session for the test user
            client.set_session({"user_id": test_user.id})
            
            # Make the request
            response = client.post(
                "/twitter/cookie",
                data={"twitter_cookie": "invalid-cookie"}
            )
            
            # Verify response indicates an error
            # The route handler wraps all exceptions in a 500 error
            assert response.status_code == 500
            assert "An unexpected error occurred" in response.json()["detail"]
            
            # Verify the mock was called correctly
            mock_create_auth.assert_called_with("twitter_cookie")
            mock_auth.validate_credentials.assert_called_once()
    
    def test_submit_cookie_update_existing(self, client, test_user, test_twitter_account):
        """Test updating an existing Twitter account's cookie"""
        # Mock the Twitter auth plugin
        with patch("plugin_manager.plugin_manager.create_authorization_plugin") as mock_create_auth:
            # Setup the mock plugin
            mock_auth = AsyncMock()
            mock_auth.validate_credentials = AsyncMock(return_value=True)
            mock_auth.get_user_identifier = AsyncMock(return_value=test_twitter_account.twitter_id)
            mock_auth.credentials_from_string = MagicMock(return_value={"cookie": "test"})
            mock_create_auth.return_value = mock_auth
            
            # Set up client session for the test user
            client.set_session({"user_id": test_user.id})
            
            # Make the request
            response = client.post(
                "/twitter/cookie",
                data={"twitter_cookie": "auth_token=newtoken; ct0=newct0"}
            )
            
            # Verify response
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            assert response.json()["message"] == "Twitter account linked successfully"
            
            # Verify mocks were called
            mock_create_auth.assert_called_with("twitter_cookie")
            mock_auth.validate_credentials.assert_called_once()
            mock_auth.get_user_identifier.assert_called_once()