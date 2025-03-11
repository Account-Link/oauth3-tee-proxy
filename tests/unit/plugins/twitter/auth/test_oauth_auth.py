"""
Unit tests for Twitter OAuth authentication
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from plugins.twitter.auth.oauth import TwitterOAuthAuthorizationPlugin

pytestmark = [pytest.mark.unit, pytest.mark.oauth_auth]


class TestTwitterOAuthAuthorizationPlugin:
    """Test the TwitterOAuthAuthorizationPlugin class"""
    
    def test_service_name(self):
        """Test that the service name is correctly set"""
        plugin = TwitterOAuthAuthorizationPlugin()
        assert plugin.service_name == "twitter_oauth"
    
    def test_credentials_to_string(self):
        """Test converting credentials to a string"""
        plugin = TwitterOAuthAuthorizationPlugin()
        credentials = {
            "oauth_token": "test-token",
            "oauth_token_secret": "test-secret",
            "user_id": "test-user-id",
            "screen_name": "test_user"
        }
        result = plugin.credentials_to_string(credentials)
        
        # Should be a JSON string
        parsed = json.loads(result)
        assert parsed["oauth_token"] == "test-token"
        assert parsed["oauth_token_secret"] == "test-secret"
        assert parsed["user_id"] == "test-user-id"
        assert parsed["screen_name"] == "test_user"
    
    def test_credentials_from_string(self):
        """Test parsing credentials from a string"""
        plugin = TwitterOAuthAuthorizationPlugin()
        credentials_str = json.dumps({
            "oauth_token": "test-token",
            "oauth_token_secret": "test-secret",
            "user_id": "test-user-id",
            "screen_name": "test_user"
        })
        result = plugin.credentials_from_string(credentials_str)
        
        assert result["oauth_token"] == "test-token"
        assert result["oauth_token_secret"] == "test-secret"
        assert result["user_id"] == "test-user-id"
        assert result["screen_name"] == "test_user"
    
    def test_credentials_from_string_with_invalid_json(self):
        """Test parsing credentials from an invalid JSON string"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        with pytest.raises(ValueError):
            plugin.credentials_from_string("invalid-json")
    
    @pytest.mark.asyncio
    async def test_get_authorization_url(self):
        """Test getting the authorization URL"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the get_oauth_handler method
        mock_handler = MagicMock()
        mock_handler.get_authorization_url.return_value = "https://twitter.com/oauth/authorize?oauth_token=test-token"
        mock_handler.request_token = {"oauth_token": "test-token", "oauth_token_secret": "test-secret"}
        
        with patch.object(plugin, 'get_oauth_handler', return_value=mock_handler):
            url, token = await plugin.get_authorization_url()
            
            assert url == "https://twitter.com/oauth/authorize?oauth_token=test-token"
            assert token == {"oauth_token": "test-token", "oauth_token_secret": "test-secret"}
            mock_handler.get_authorization_url.assert_called_once_with(signin_with_twitter=True)
    
    @pytest.mark.asyncio
    async def test_get_authorization_url_with_callback(self):
        """Test getting the authorization URL with a custom callback"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the get_oauth_handler method
        mock_handler = MagicMock()
        mock_handler.get_authorization_url.return_value = "https://twitter.com/oauth/authorize?oauth_token=test-token"
        mock_handler.request_token = {"oauth_token": "test-token", "oauth_token_secret": "test-secret"}
        
        with patch.object(plugin, 'get_oauth_handler', return_value=mock_handler):
            url, token = await plugin.get_authorization_url("https://example.com/callback")
            
            assert url == "https://twitter.com/oauth/authorize?oauth_token=test-token"
            assert token == {"oauth_token": "test-token", "oauth_token_secret": "test-secret"}
            plugin.get_oauth_handler.assert_called_once_with("https://example.com/callback")
    
    @pytest.mark.asyncio
    async def test_process_callback(self):
        """Test processing the OAuth callback"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the get_oauth_handler method
        mock_handler = MagicMock()
        mock_handler.get_access_token.return_value = ("test-access-token", "test-access-secret")
        
        # Mock the get_user_info method
        plugin.get_user_info = AsyncMock(return_value={
            "id": "test-user-id",
            "screen_name": "test_user",
            "name": "Test User",
            "profile_image_url": "https://example.com/image.jpg"
        })
        
        with patch.object(plugin, 'get_oauth_handler', return_value=mock_handler):
            request_token = {"oauth_token": "test-token", "oauth_token_secret": "test-secret"}
            oauth_verifier = "test-verifier"
            
            result = await plugin.process_callback(request_token, oauth_verifier)
            
            assert result["oauth_token"] == "test-access-token"
            assert result["oauth_token_secret"] == "test-access-secret"
            assert result["user_id"] == "test-user-id"
            assert result["screen_name"] == "test_user"
            assert result["name"] == "Test User"
            assert result["profile_image_url"] == "https://example.com/image.jpg"
            
            mock_handler.get_access_token.assert_called_once_with("test-verifier")
            plugin.get_user_info.assert_called_once_with("test-access-token", "test-access-secret")
    
    @pytest.mark.asyncio
    async def test_process_callback_failure(self):
        """Test processing the OAuth callback with a failure"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the get_oauth_handler method
        mock_handler = MagicMock()
        mock_handler.get_access_token.side_effect = Exception("Token error")
        
        with patch.object(plugin, 'get_oauth_handler', return_value=mock_handler):
            request_token = {"oauth_token": "test-token", "oauth_token_secret": "test-secret"}
            oauth_verifier = "test-verifier"
            
            with pytest.raises(ValueError):
                await plugin.process_callback(request_token, oauth_verifier)
    
    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test getting user information"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the Twitter API client
        mock_api = MagicMock()
        mock_api.verify_credentials.return_value = MagicMock(
            id_str="test-user-id",
            screen_name="test_user",
            name="Test User",
            profile_image_url_https="https://example.com/image.jpg"
        )
        
        with patch('tweepy.API', return_value=mock_api):
            result = await plugin.get_user_info("test-token", "test-secret")
            
            assert result["id"] == "test-user-id"
            assert result["screen_name"] == "test_user"
            assert result["name"] == "Test User"
            assert result["profile_image_url"] == "https://example.com/image.jpg"
    
    @pytest.mark.asyncio
    async def test_get_user_info_failure(self):
        """Test getting user information with a failure"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the Twitter API client
        mock_api = MagicMock()
        mock_api.verify_credentials.side_effect = Exception("API error")
        
        with patch('tweepy.API', return_value=mock_api):
            with pytest.raises(ValueError):
                await plugin.get_user_info("test-token", "test-secret")
    
    @pytest.mark.asyncio
    async def test_validate_credentials(self):
        """Test validating credentials"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the get_user_info method
        plugin.get_user_info = AsyncMock(return_value={
            "id": "test-user-id",
            "screen_name": "test_user"
        })
        
        credentials = {
            "oauth_token": "test-token",
            "oauth_token_secret": "test-secret"
        }
        
        result = await plugin.validate_credentials(credentials)
        
        assert result is True
        plugin.get_user_info.assert_called_once_with("test-token", "test-secret")
    
    @pytest.mark.asyncio
    async def test_validate_credentials_missing_tokens(self):
        """Test validating credentials with missing tokens"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        credentials = {}
        
        result = await plugin.validate_credentials(credentials)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_credentials_failure(self):
        """Test validating credentials with a failure"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the get_user_info method
        plugin.get_user_info = AsyncMock(side_effect=Exception("API error"))
        
        credentials = {
            "oauth_token": "test-token",
            "oauth_token_secret": "test-secret"
        }
        
        result = await plugin.validate_credentials(credentials)
        
        assert result is False
        plugin.get_user_info.assert_called_once_with("test-token", "test-secret")
    
    @pytest.mark.asyncio
    async def test_get_user_identifier_from_credentials(self):
        """Test getting the user identifier from credentials"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        credentials = {
            "oauth_token": "test-token",
            "oauth_token_secret": "test-secret",
            "user_id": "test-user-id"
        }
        
        result = await plugin.get_user_identifier(credentials)
        
        assert result == "test-user-id"
    
    @pytest.mark.asyncio
    async def test_get_user_identifier_from_api(self):
        """Test getting the user identifier from the API"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the get_user_info method
        plugin.get_user_info = AsyncMock(return_value={
            "id": "test-user-id",
            "screen_name": "test_user"
        })
        
        credentials = {
            "oauth_token": "test-token",
            "oauth_token_secret": "test-secret"
        }
        
        result = await plugin.get_user_identifier(credentials)
        
        assert result == "test-user-id"
        plugin.get_user_info.assert_called_once_with("test-token", "test-secret")
    
    @pytest.mark.asyncio
    async def test_get_user_identifier_failure(self):
        """Test getting the user identifier with a failure"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the get_user_info method
        plugin.get_user_info = AsyncMock(side_effect=Exception("API error"))
        
        credentials = {
            "oauth_token": "test-token",
            "oauth_token_secret": "test-secret"
        }
        
        with pytest.raises(ValueError):
            await plugin.get_user_identifier(credentials)
    
    @pytest.mark.asyncio
    async def test_refresh_credentials_valid(self):
        """Test refreshing valid credentials"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the validate_credentials method
        plugin.validate_credentials = AsyncMock(return_value=True)
        
        credentials = {
            "oauth_token": "test-token",
            "oauth_token_secret": "test-secret"
        }
        
        result = await plugin.refresh_credentials(credentials)
        
        assert result == credentials
        plugin.validate_credentials.assert_called_once_with(credentials)
    
    @pytest.mark.asyncio
    async def test_refresh_credentials_invalid(self):
        """Test refreshing invalid credentials"""
        plugin = TwitterOAuthAuthorizationPlugin()
        
        # Mock the validate_credentials method
        plugin.validate_credentials = AsyncMock(return_value=False)
        
        credentials = {
            "oauth_token": "test-token",
            "oauth_token_secret": "test-secret"
        }
        
        with pytest.raises(ValueError):
            await plugin.refresh_credentials(credentials)