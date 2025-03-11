"""
Integration tests for Twitter OAuth authentication routes
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import json

pytestmark = [pytest.mark.integration, pytest.mark.oauth_auth]


class TestTwitterOAuthRoutes:
    """Test the Twitter OAuth authentication routes"""
    
    def test_oauth_login_route(self, client, mock_twitter_oauth_auth_plugin):
        """Test the OAuth login route"""
        # Make get_authorization_url return a test URL and token
        mock_twitter_oauth_auth_plugin.get_authorization_url = AsyncMock(
            return_value=("https://twitter.com/oauth/authorize?oauth_token=test-token", {"oauth_token": "test-token"})
        )
        
        response = client.get(
            "/twitter/oauth/login",
            params={"next": "/dashboard"}
        )
        
        # Should redirect to Twitter
        assert response.status_code == 307
        assert response.headers["location"] == "https://twitter.com/oauth/authorize?oauth_token=test-token"
        
        # The session should be set
        assert client.cookies.get("session") is not None
    
    def test_oauth_link_route_authenticated(self, client, test_user, mock_twitter_oauth_auth_plugin):
        """Test the OAuth link route when authenticated"""
        # Make get_authorization_url return a test URL and token
        mock_twitter_oauth_auth_plugin.get_authorization_url = AsyncMock(
            return_value=("https://twitter.com/oauth/authorize?oauth_token=test-token", {"oauth_token": "test-token"})
        )
        
        # Set up a session for the test user
        client.cookies.update({"session": "test-session"})
        with patch("fastapi.Request.session", {"user_id": test_user.id}):
            response = client.get(
                "/twitter/oauth/link",
                params={"next": "/dashboard"}
            )
            
            # Should redirect to Twitter
            assert response.status_code == 307
            assert response.headers["location"] == "https://twitter.com/oauth/authorize?oauth_token=test-token"
    
    def test_oauth_link_route_unauthenticated(self, client, mock_twitter_oauth_auth_plugin):
        """Test the OAuth link route when not authenticated"""
        response = client.get(
            "/twitter/oauth/link",
            params={"next": "/dashboard"}
        )
        
        # Should return unauthorized
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    
    def test_oauth_callback_new_user(self, client, test_db, mock_twitter_oauth_auth_plugin):
        """Test the OAuth callback route for a new user"""
        # Mock the plugin methods
        mock_twitter_oauth_auth_plugin.process_callback = AsyncMock(
            return_value={
                "oauth_token": "test-access-token",
                "oauth_token_secret": "test-access-secret",
                "user_id": "new-twitter-id",
                "screen_name": "new_user"
            }
        )
        
        # Set up session with the request token
        client.cookies.update({"session": "test-session"})
        with patch("fastapi.Request.session", {
            "twitter_request_token": {"oauth_token": "test-token"},
            "twitter_auth_flow": "login",
            "twitter_auth_next": "/dashboard"
        }):
            response = client.get(
                "/twitter/oauth/callback",
                params={
                    "oauth_token": "test-token",
                    "oauth_verifier": "test-verifier"
                }
            )
            
            # Should redirect to the next URL
            assert response.status_code == 303
            assert response.headers["location"] == "/dashboard"
            
            # Check that a new user and Twitter account were created
            from models import User
            from plugins.twitter.models import TwitterAccount, TwitterOAuthCredential
            
            user = test_db.query(User).filter(User.username == "twitter_new_user").first()
            assert user is not None
            
            twitter_account = test_db.query(TwitterAccount).filter(TwitterAccount.twitter_id == "new-twitter-id").first()
            assert twitter_account is not None
            assert twitter_account.user_id == user.id
            assert twitter_account.can_login is True
            
            oauth_cred = test_db.query(TwitterOAuthCredential).filter(
                TwitterOAuthCredential.twitter_account_id == "new-twitter-id"
            ).first()
            assert oauth_cred is not None
            assert oauth_cred.oauth_token == "test-access-token"
            assert oauth_cred.oauth_token_secret == "test-access-secret"
    
    def test_oauth_callback_existing_account_login(self, client, test_db, test_twitter_account, mock_twitter_oauth_auth_plugin):
        """Test the OAuth callback route for an existing Twitter account (login flow)"""
        # Mock the plugin methods
        mock_twitter_oauth_auth_plugin.process_callback = AsyncMock(
            return_value={
                "oauth_token": "test-access-token",
                "oauth_token_secret": "test-access-secret",
                "user_id": test_twitter_account.twitter_id,
                "screen_name": "existing_user"
            }
        )
        
        # Set up session with the request token
        client.cookies.update({"session": "test-session"})
        with patch("fastapi.Request.session", {
            "twitter_request_token": {"oauth_token": "test-token"},
            "twitter_auth_flow": "login",
            "twitter_auth_next": "/dashboard"
        }):
            response = client.get(
                "/twitter/oauth/callback",
                params={
                    "oauth_token": "test-token",
                    "oauth_verifier": "test-verifier"
                }
            )
            
            # Should redirect to the next URL
            assert response.status_code == 303
            assert response.headers["location"] == "/dashboard"
            
            # Check that the OAuth credentials were created
            from plugins.twitter.models import TwitterOAuthCredential
            
            oauth_cred = test_db.query(TwitterOAuthCredential).filter(
                TwitterOAuthCredential.twitter_account_id == test_twitter_account.twitter_id
            ).first()
            assert oauth_cred is not None
            assert oauth_cred.oauth_token == "test-access-token"
            assert oauth_cred.oauth_token_secret == "test-access-secret"
    
    def test_oauth_callback_link_to_existing_user(self, client, test_db, test_user, mock_twitter_oauth_auth_plugin):
        """Test the OAuth callback route for linking to an existing user"""
        # Mock the plugin methods
        mock_twitter_oauth_auth_plugin.process_callback = AsyncMock(
            return_value={
                "oauth_token": "test-access-token",
                "oauth_token_secret": "test-access-secret",
                "user_id": "new-twitter-id",
                "screen_name": "new_user"
            }
        )
        
        # Set up session with the request token and user ID
        client.cookies.update({"session": "test-session"})
        with patch("fastapi.Request.session", {
            "twitter_request_token": {"oauth_token": "test-token"},
            "twitter_auth_flow": "link",
            "twitter_auth_next": "/dashboard",
            "user_id": test_user.id
        }):
            response = client.get(
                "/twitter/oauth/callback",
                params={
                    "oauth_token": "test-token",
                    "oauth_verifier": "test-verifier"
                }
            )
            
            # Should redirect to the next URL
            assert response.status_code == 303
            assert response.headers["location"] == "/dashboard"
            
            # Check that a new Twitter account was created and linked to the existing user
            from plugins.twitter.models import TwitterAccount, TwitterOAuthCredential
            
            twitter_account = test_db.query(TwitterAccount).filter(TwitterAccount.twitter_id == "new-twitter-id").first()
            assert twitter_account is not None
            assert twitter_account.user_id == test_user.id
            assert twitter_account.can_login is True
            
            oauth_cred = test_db.query(TwitterOAuthCredential).filter(
                TwitterOAuthCredential.twitter_account_id == "new-twitter-id"
            ).first()
            assert oauth_cred is not None
            assert oauth_cred.oauth_token == "test-access-token"
            assert oauth_cred.oauth_token_secret == "test-access-secret"
    
    def test_oauth_callback_invalid_params(self, client):
        """Test the OAuth callback route with invalid parameters"""
        response = client.get(
            "/twitter/oauth/callback",
            params={
                "oauth_token": "test-token"
                # Missing oauth_verifier
            }
        )
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Missing OAuth parameters"
    
    def test_oauth_callback_missing_request_token(self, client):
        """Test the OAuth callback route with a missing request token in the session"""
        response = client.get(
            "/twitter/oauth/callback",
            params={
                "oauth_token": "test-token",
                "oauth_verifier": "test-verifier"
            }
        )
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid session state"