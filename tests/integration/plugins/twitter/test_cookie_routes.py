"""
Integration tests for Twitter cookie authentication routes
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.integration, pytest.mark.cookie_auth]


class TestTwitterCookieRoutes:
    """Test the Twitter cookie authentication routes"""
    
    def test_submit_cookie_success(self, client, test_user, mock_twitter_cookie_auth_plugin):
        """Test submitting a cookie successfully"""
        # Set up a session for the test user
        client.cookies.update({"session": "test-session"})
        with patch("fastapi.Request.session", {"user_id": test_user.id}):
            response = client.post(
                "/twitter/cookie",
                data={"twitter_cookie": "auth_token=abcdef; ct0=123456"}
            )
            
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            assert response.json()["message"] == "Twitter account linked successfully"
    
    def test_submit_cookie_no_auth(self, client, mock_twitter_cookie_auth_plugin):
        """Test submitting a cookie without authentication"""
        response = client.post(
            "/twitter/cookie",
            data={"twitter_cookie": "auth_token=abcdef; ct0=123456"}
        )
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    def test_submit_cookie_invalid(self, client, test_user, mock_twitter_cookie_auth_plugin):
        """Test submitting an invalid cookie"""
        # Make validate_credentials return False
        mock_twitter_cookie_auth_plugin.validate_credentials = MagicMock(return_value=False)
        
        # Set up a session for the test user
        client.cookies.update({"session": "test-session"})
        with patch("fastapi.Request.session", {"user_id": test_user.id}):
            response = client.post(
                "/twitter/cookie",
                data={"twitter_cookie": "invalid-cookie"}
            )
            
            assert response.status_code == 400
            assert "Invalid Twitter cookie" in response.json()["detail"]
    
    def test_submit_cookie_update_existing(self, client, test_user, test_twitter_account, mock_twitter_cookie_auth_plugin):
        """Test updating an existing Twitter account's cookie"""
        # Set up a session for the test user
        client.cookies.update({"session": "test-session"})
        with patch("fastapi.Request.session", {"user_id": test_user.id}):
            response = client.post(
                "/twitter/cookie",
                data={"twitter_cookie": "auth_token=newtoken; ct0=newct0"}
            )
            
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            assert response.json()["message"] == "Twitter account linked successfully"