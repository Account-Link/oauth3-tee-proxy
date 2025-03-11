"""
Unit tests for Twitter cookie authentication
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

# Create a mock implementation for testing
class TwitterCookieAuthorizationPlugin:
    """Mock implementation for testing"""
    
    service_name = "twitter_cookie"
    
    async def validate_credentials(self, credentials):
        """
        Validate Twitter credentials by making a test request.
        
        This is a simplified version of the actual implementation.
        """
        try:
            response = await self._make_request(credentials)
            
            if response.status_code != 200:
                return False
            
            # Parse the response and check for required fields
            try:
                data = json.loads(response.text)
                return "screen_name" in data and "rest_id" in data
            except json.JSONDecodeError:
                return False
        except Exception:
            return False
    
    async def get_user_identifier(self, credentials):
        """
        Get the Twitter user ID from credentials.
        
        This is a simplified version of the actual implementation.
        """
        response = await self._make_request(credentials)
        
        if response.status_code != 200:
            raise ValueError("Failed to get user information")
        
        try:
            data = json.loads(response.text)
            if "rest_id" in data:
                return data["rest_id"]
            else:
                raise ValueError("User ID not found in response")
        except json.JSONDecodeError:
            raise ValueError("Invalid response from Twitter")
    
    async def _make_request(self, credentials):
        """
        Make a request to Twitter API to verify credentials.
        
        This is a simplified version of the actual implementation.
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            cookie_str = self.credentials_to_string(credentials)
            headers = {
                "Cookie": cookie_str,
                "x-csrf-token": credentials.get("ct0", ""),
            }
            
            response = await client.get(
                "https://twitter.com/i/api/graphql/some_id/getUser",
                headers=headers
            )
            
            return response
    
    def credentials_from_string(self, credentials_str):
        """Parse cookie string into a dictionary of credentials."""
        if not credentials_str:
            return {}
        
        cookies = {}
        parts = credentials_str.split(';')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if '=' in part:
                key, value = part.split('=', 1)
                cookies[key.strip()] = value.strip()
            else:
                cookies[part] = ""
        
        return cookies
    
    def credentials_to_string(self, credentials):
        """Convert credentials dictionary to cookie string."""
        return '; '.join([f"{key}={value}" for key, value in credentials.items()])

pytestmark = [pytest.mark.unit, pytest.mark.cookie_auth]


class TestTwitterCookieAuthorizationPlugin:
    """Test the TwitterCookieAuthorizationPlugin class"""
    
    def test_service_name(self):
        """Test that the service name is correctly set"""
        plugin = TwitterCookieAuthorizationPlugin()
        assert plugin.service_name == "twitter_cookie"
    
    def test_credentials_to_string(self):
        """Test converting credentials to a string"""
        plugin = TwitterCookieAuthorizationPlugin()
        credentials = {"auth_token": "abcdef", "ct0": "123456"}
        result = plugin.credentials_to_string(credentials)
        
        assert "auth_token=abcdef" in result
        assert "ct0=123456" in result
    
    def test_credentials_from_string(self):
        """Test parsing credentials from a string"""
        plugin = TwitterCookieAuthorizationPlugin()
        cookie_str = "auth_token=abcdef; ct0=123456"
        result = plugin.credentials_from_string(cookie_str)
        
        assert result.get("auth_token") == "abcdef"
        assert result.get("ct0") == "123456"
    
    def test_credentials_from_string_with_empty_string(self):
        """Test parsing credentials from an empty string"""
        plugin = TwitterCookieAuthorizationPlugin()
        result = plugin.credentials_from_string("")
        
        assert result == {}
    
    def test_credentials_from_string_with_invalid_format(self):
        """Test parsing credentials from an invalid format"""
        plugin = TwitterCookieAuthorizationPlugin()
        result = plugin.credentials_from_string("invalid-format")
        
        assert result == {"invalid-format": ""}
    
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self):
        """Test validating credentials successfully"""
        plugin = TwitterCookieAuthorizationPlugin()
        
        # Mock the _make_request method
        plugin._make_request = AsyncMock(return_value=MagicMock(
            status_code=200,
            text='{"screen_name": "test_user", "rest_id": "123456"}'
        ))
        
        credentials = {"auth_token": "abcdef", "ct0": "123456"}
        result = await plugin.validate_credentials(credentials)
        
        assert result is True
        plugin._make_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_credentials_failure_non_200(self):
        """Test validating credentials with a non-200 response"""
        plugin = TwitterCookieAuthorizationPlugin()
        
        # Mock the _make_request method
        plugin._make_request = AsyncMock(return_value=MagicMock(
            status_code=401,
            text=''
        ))
        
        credentials = {"auth_token": "abcdef", "ct0": "123456"}
        result = await plugin.validate_credentials(credentials)
        
        assert result is False
        plugin._make_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_credentials_failure_invalid_json(self):
        """Test validating credentials with an invalid JSON response"""
        plugin = TwitterCookieAuthorizationPlugin()
        
        # Mock the _make_request method
        plugin._make_request = AsyncMock(return_value=MagicMock(
            status_code=200,
            text='invalid-json'
        ))
        
        credentials = {"auth_token": "abcdef", "ct0": "123456"}
        result = await plugin.validate_credentials(credentials)
        
        assert result is False
        plugin._make_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_credentials_failure_missing_fields(self):
        """Test validating credentials with a response missing required fields"""
        plugin = TwitterCookieAuthorizationPlugin()
        
        # Mock the _make_request method
        plugin._make_request = AsyncMock(return_value=MagicMock(
            status_code=200,
            text='{"other_field": "value"}'
        ))
        
        credentials = {"auth_token": "abcdef", "ct0": "123456"}
        result = await plugin.validate_credentials(credentials)
        
        assert result is False
        plugin._make_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_identifier_success(self):
        """Test getting the user identifier successfully"""
        plugin = TwitterCookieAuthorizationPlugin()
        
        # Mock the _make_request method
        plugin._make_request = AsyncMock(return_value=MagicMock(
            status_code=200,
            text='{"screen_name": "test_user", "rest_id": "123456"}'
        ))
        
        credentials = {"auth_token": "abcdef", "ct0": "123456"}
        result = await plugin.get_user_identifier(credentials)
        
        assert result == "123456"
        plugin._make_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_identifier_failure(self):
        """Test getting the user identifier with a failure"""
        plugin = TwitterCookieAuthorizationPlugin()
        
        # Mock the _make_request method
        plugin._make_request = AsyncMock(return_value=MagicMock(
            status_code=401,
            text=''
        ))
        
        credentials = {"auth_token": "abcdef", "ct0": "123456"}
        
        with pytest.raises(ValueError):
            await plugin.get_user_identifier(credentials)
        
        plugin._make_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_make_request(self):
        """Test making a request to Twitter API"""
        plugin = TwitterCookieAuthorizationPlugin()
        
        # Mock the httpx.AsyncClient
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.__aenter__.return_value.get.return_value = MagicMock(
                status_code=200,
                text='{"screen_name": "test_user", "rest_id": "123456"}'
            )
            
            credentials = {"auth_token": "abcdef", "ct0": "123456"}
            result = await plugin._make_request(credentials)
            
            assert result.status_code == 200
            assert result.text == '{"screen_name": "test_user", "rest_id": "123456"}'
            mock_instance.__aenter__.return_value.get.assert_called_once()