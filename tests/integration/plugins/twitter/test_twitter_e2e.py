"""
End-to-end integration tests for Twitter plugin functionality.

These tests verify the complete flow from adding a Twitter account via cookie 
to viewing that account on the dashboard, ensuring that the entire system works together.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from bs4 import BeautifulSoup

from models import User
from plugins.twitter.models import TwitterAccount

# Import telegram models to ensure tables are created
from plugins.telegram.models import TelegramAccount, TelegramChannel

pytestmark = [pytest.mark.integration]


class TestTwitterE2E:
    """End-to-end tests for Twitter plugin functionality."""
    
    def test_add_twitter_account_e2e(self, client, test_user, test_db):
        """
        Test adding a Twitter account via cookie submission.
        
        This test verifies:
        1. User can submit a Twitter cookie
        2. Cookie is processed correctly
        3. Twitter account is added to the database with correct information
        4. The dashboard shows the Twitter plugin card
        """
        # Setup: Mock the Twitter auth plugin for cookie validation
        with patch("plugin_manager.plugin_manager.create_authorization_plugin") as mock_create_auth:
            # Setup the mock plugin with test data
            mock_auth = AsyncMock()
            mock_auth.validate_credentials = AsyncMock(return_value=True)
            mock_auth.get_user_identifier = AsyncMock(return_value="123456789")
            mock_auth.get_user_profile = AsyncMock(return_value={
                "username": "testuser",
                "name": "Test Twitter User",
                "profile_image_url": "https://example.com/avatar.jpg"
            })
            mock_auth.credentials_from_string = MagicMock(return_value={"cookie": "test"})
            mock_create_auth.return_value = mock_auth
            
            # Set up client session for the test user
            client.set_session({"user_id": test_user.id})
            
            # Step 1: Submit the Twitter cookie
            response = client.post(
                "/twitter/auth/cookies",
                data={"twitter_cookie": "auth_token=test_auth_token"},
                allow_redirects=False
            )
            
            # Verify the redirect to dashboard after successful submission
            assert response.status_code == 303
            assert response.headers["location"] == "/dashboard"
            
            # Step 2: Verify the account was created in the database
            account = test_db.query(TwitterAccount).filter_by(twitter_id="123456789").first()
            assert account is not None, "Twitter account not created in database"
            assert account.user_id == test_user.id, "Twitter account not linked to correct user"
            assert account.username == "testuser", "Username not stored correctly"
            assert account.display_name == "Test Twitter User", "Display name not stored correctly"
            assert account.profile_image_url == "https://example.com/avatar.jpg", "Profile image URL not stored correctly"
            
            # Step 3: Load the dashboard
            dashboard_response = client.get("/dashboard")
            assert dashboard_response.status_code == 200
            
            # Step 4: Check that the Twitter plugin is displayed in the dashboard
            soup = BeautifulSoup(dashboard_response.content, "html.parser")
            
            # Find the Twitter plugin card
            twitter_plugin_card = soup.find("div", attrs={"data-plugin": "twitter"})
            assert twitter_plugin_card is not None, "Twitter plugin card not found on dashboard"
            
            # Verify the Add Twitter Account link exists and points to the correct URL
            add_account_link = twitter_plugin_card.find("a", href="/twitter/auth/admin")
            assert add_account_link is not None, "Add Twitter Account link not found in Twitter plugin card"
            assert "Add Twitter Account" in add_account_link.text, "Add Twitter Account text not found in link"