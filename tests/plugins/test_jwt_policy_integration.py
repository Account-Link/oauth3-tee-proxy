"""
Test JWT Policy Integration with Plugins
=====================================

This module tests that plugins correctly implement JWT policy scopes
and that the plugin manager properly collects and processes them.
"""

import pytest
from unittest.mock import MagicMock, patch

from plugin_manager import plugin_manager
from plugins import RoutePlugin

class MockTwitterPlugin(RoutePlugin):
    """Mock Twitter plugin for testing."""
    
    def get_routers(self):
        return {"twitter": MagicMock()}
    
    def get_auth_requirements(self):
        return {
            "/api/*": ["passkey", "api"]
        }
    
    def get_jwt_policy_scopes(self):
        return {
            "twitter-read": {"tweet.read"},
            "twitter-write": {"tweet.post", "tweet.delete"}
        }

class MockTelegramPlugin(RoutePlugin):
    """Mock Telegram plugin for testing."""
    
    def get_routers(self):
        return {"telegram": MagicMock()}
    
    def get_auth_requirements(self):
        return {
            "/send/*": ["api"]
        }
    
    def get_jwt_policy_scopes(self):
        return {
            "telegram-admin": {"telegram.post_any"},
            "full-access": {"tweet.read", "telegram.post_any"}  # Overlapping policy
        }

class TestJWTPolicyIntegration:
    """Test JWT policy integration with plugins."""
    
    @pytest.fixture
    def mock_plugins(self):
        """Set up mock plugins for testing."""
        original_plugins = plugin_manager.plugins
        
        # Mock the plugins list
        plugin_manager.plugins = [
            MockTwitterPlugin(),
            MockTelegramPlugin()
        ]
        
        yield
        
        # Restore original plugins
        plugin_manager.plugins = original_plugins
    
    def test_get_jwt_policy_scopes(self, mock_plugins):
        """Test that plugin manager correctly collects JWT policy scopes."""
        # Get JWT policy scopes
        policy_scopes = plugin_manager.get_jwt_policy_scopes()
        
        # Verify default policies exist
        assert "passkey" in policy_scopes
        assert "api" in policy_scopes
        
        # Verify plugin-specific policies
        assert "twitter-read" in policy_scopes
        assert "twitter-write" in policy_scopes
        assert "telegram-admin" in policy_scopes
        assert "full-access" in policy_scopes
        
        # Verify scope content
        assert "tweet.read" in policy_scopes["twitter-read"]
        assert "tweet.post" in policy_scopes["twitter-write"]
        assert "telegram.post_any" in policy_scopes["telegram-admin"]
        
        # Verify overlapping policy has all scopes
        assert "tweet.read" in policy_scopes["full-access"]
        assert "telegram.post_any" in policy_scopes["full-access"]
    
    def test_auth_requirements_conversion(self, mock_plugins):
        """Test that auth requirements are correctly converted to new format."""
        # Get auth requirements
        auth_requirements = plugin_manager.get_auth_requirements()
        
        # Verify paths
        assert "/twitter/api/*" in auth_requirements
        assert "/telegram/send/*" in auth_requirements
        
        # Verify auth types
        assert "passkey" in auth_requirements["/twitter/api/*"]
        assert "api" in auth_requirements["/twitter/api/*"]
        assert "api" in auth_requirements["/telegram/send/*"]
    
    @patch("plugin_manager.plugin_manager.get_all_plugin_scopes")
    def test_api_policy_has_all_scopes(self, mock_get_scopes, mock_plugins):
        """Test that 'api' policy has all available scopes."""
        # Mock the get_all_plugin_scopes method
        mock_get_scopes.return_value = {
            "scope1": "Description 1",
            "scope2": "Description 2",
            "scope3": "Description 3"
        }
        
        # Get JWT policy scopes
        policy_scopes = plugin_manager.get_jwt_policy_scopes()
        
        # Verify 'api' policy has all scopes
        assert "scope1" in policy_scopes["api"]
        assert "scope2" in policy_scopes["api"]
        assert "scope3" in policy_scopes["api"]