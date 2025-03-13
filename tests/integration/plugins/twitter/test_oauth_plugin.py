"""
Integration tests for Twitter OAuth plugin functionality
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from fastapi import Request, Response, HTTPException
from fastapi.responses import RedirectResponse

# Import models to ensure they're registered
from models import User
from plugins.twitter.models import TwitterAccount, TwitterOAuthCredential
from plugins.telegram.models import TelegramAccount, TelegramChannel

# Import the route plugin and auth plugin
from plugins.twitter.routes.oauth_routes import TwitterOAuthRoutes
from sqlalchemy.orm import Session

pytestmark = [pytest.mark.integration, pytest.mark.oauth_auth]


class TestTwitterOAuthPlugin:
    """Test the Twitter OAuth authentication functionality at the plugin level"""
    
    def test_oauth_login_route(self, monkeypatch):
        """Test the Twitter OAuth login function directly"""
        # Create route handler
        router = TwitterOAuthRoutes().get_router()
        
        # Debug: Print route paths
        print("Available route paths:")
        for route in router.routes:
            print(f"Path: {route.path} -> {route.methods}")
            
        # Find the route function
        login_handler = None
        for route in router.routes:
            if "/login" in route.path and "GET" in route.methods:
                login_handler = route.endpoint
                break
        
        assert login_handler is not None, "Could not find login route handler"
        
        # Mock plugin manager
        with patch("plugin_manager.plugin_manager") as mock_plugin_manager:
            # Set up mock auth plugin
            mock_oauth_auth = AsyncMock()
            mock_oauth_auth.get_authorization_url = AsyncMock(
                return_value=("https://twitter.com/oauth/authorize?oauth_token=test-token", {"oauth_token": "test-token"})
            )
            mock_plugin_manager.create_authorization_plugin.return_value = mock_oauth_auth
            
            # Create mock request
            mock_request = MagicMock()
            mock_request.session = {}
            
            # Call handler directly
            response = asyncio.run(login_handler(
                request=mock_request,
                next="/dashboard"
            ))
            
            # Verify response
            assert isinstance(response, RedirectResponse)
            assert response.status_code == 307
            assert response.headers["location"] == "https://twitter.com/oauth/authorize?oauth_token=test-token"
            
            # Check session was updated
            assert "twitter_request_token" in mock_request.session
            assert "twitter_auth_flow" in mock_request.session
            assert mock_request.session["twitter_auth_flow"] == "login"
            assert mock_request.session["twitter_auth_next"] == "/dashboard"
            
            # Verify mocks were called correctly
            mock_plugin_manager.create_authorization_plugin.assert_called_with("twitter_oauth")
            mock_oauth_auth.get_authorization_url.assert_called_once()
    
    def test_oauth_link_route_authenticated(self, monkeypatch):
        """Test the Twitter OAuth link function directly with an authenticated user"""
        # Create route handler
        router = TwitterOAuthRoutes().get_router()
        
        # Find the route function
        link_handler = None
        for route in router.routes:
            if "/link" in route.path and "GET" in route.methods:
                link_handler = route.endpoint
                break
        
        assert link_handler is not None, "Could not find link route handler"
        
        # Mock plugin manager
        with patch("plugin_manager.plugin_manager") as mock_plugin_manager:
            # Set up mock auth plugin
            mock_oauth_auth = AsyncMock()
            mock_oauth_auth.get_authorization_url = AsyncMock(
                return_value=("https://twitter.com/oauth/authorize?oauth_token=test-token", {"oauth_token": "test-token"})
            )
            mock_plugin_manager.create_authorization_plugin.return_value = mock_oauth_auth
            
            # Create mock request with user session
            mock_request = MagicMock()
            mock_request.session = {"user_id": "test-user-id"}
            
            # Call handler directly
            response = asyncio.run(link_handler(
                request=mock_request,
                next="/dashboard"
            ))
            
            # Verify response
            assert isinstance(response, RedirectResponse)
            assert response.status_code == 307
            assert response.headers["location"] == "https://twitter.com/oauth/authorize?oauth_token=test-token"
            
            # Check session was updated
            assert "twitter_request_token" in mock_request.session
            assert "twitter_auth_flow" in mock_request.session
            assert mock_request.session["twitter_auth_flow"] == "link"
            assert mock_request.session["twitter_auth_next"] == "/dashboard"
            
            # Verify mocks were called correctly
            mock_plugin_manager.create_authorization_plugin.assert_called_with("twitter_oauth")
            mock_oauth_auth.get_authorization_url.assert_called_once()
    
    def test_oauth_link_route_unauthenticated(self, monkeypatch):
        """Test the Twitter OAuth link function directly with an unauthenticated user"""
        # Create route handler
        router = TwitterOAuthRoutes().get_router()
        
        # Find the route function
        link_handler = None
        for route in router.routes:
            if "/link" in route.path and "GET" in route.methods:
                link_handler = route.endpoint
                break
        
        assert link_handler is not None, "Could not find link route handler"
        
        # Create mock request with empty session (no user)
        mock_request = MagicMock()
        mock_request.session = {}
        
        # Call handler directly and expect an exception
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(link_handler(
                request=mock_request,
                next="/dashboard"
            ))
        
        # Verify exception
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"
    
    def test_oauth_callback_missing_parameters(self, monkeypatch):
        """Test the Twitter OAuth callback without required parameters"""
        # Create route handler
        router = TwitterOAuthRoutes().get_router()
        
        # Find the route function
        callback_handler = None
        for route in router.routes:
            if "/callback" in route.path and "GET" in route.methods:
                callback_handler = route.endpoint
                break
        
        assert callback_handler is not None, "Could not find callback route handler"
        
        # Create mock request and db
        mock_request = MagicMock()
        mock_db = MagicMock()
        
        # For this test we need to mock the plugin to properly handle the parameter validation
        with patch("plugin_manager.plugin_manager") as mock_plugin_manager:
            # Don't actually call the OAuth plugin, just raise an error about missing params
            mock_plugin_manager.create_authorization_plugin.side_effect = ValueError("Missing oauth_verifier parameter")
            
            # Call handler directly with missing oauth_verifier
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(callback_handler(
                    request=mock_request,
                    oauth_token="test-token",  # Missing oauth_verifier
                    oauth_verifier=None,  # Explicitly pass None to trigger validation
                    db=mock_db
                ))
            
            # Verify exception
            assert exc_info.value.status_code == 400
            assert "Missing OAuth parameters" in exc_info.value.detail
    
    def test_oauth_callback_missing_request_token(self, monkeypatch):
        """Test the Twitter OAuth callback with missing request token in session"""
        # Create route handler
        router = TwitterOAuthRoutes().get_router()
        
        # Find the route function
        callback_handler = None
        for route in router.routes:
            if "/callback" in route.path and "GET" in route.methods:
                callback_handler = route.endpoint
                break
        
        assert callback_handler is not None, "Could not find callback route handler"
        
        # Create mock request with empty session
        mock_request = MagicMock()
        mock_request.session = {}  # No request token
        mock_db = MagicMock()
        
        # Call handler directly
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(callback_handler(
                request=mock_request,
                oauth_token="test-token",
                oauth_verifier="test-verifier",
                db=mock_db
            ))
        
        # Verify exception
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid session state"