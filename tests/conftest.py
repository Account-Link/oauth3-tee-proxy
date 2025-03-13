"""
Shared pytest fixtures and configuration
"""

import asyncio
import pytest
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add the project root to Python path to make imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Dict, Any, Generator, AsyncGenerator

from database import Base, get_db
from models import User, WebAuthnCredential

# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TWITTER_CONSUMER_KEY"] = "test_consumer_key"
os.environ["TWITTER_CONSUMER_SECRET"] = "test_consumer_secret"
os.environ["TWITTER_OAUTH_CALLBACK_URL"] = "http://testserver/twitter/oauth/callback"

# Create in-memory SQLite database for testing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    """
    Create all tables in the test database and provide a new session for testing.
    Tear down the tables after the test is complete.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    try:
        # Create a new session for testing
        session = TestingSessionLocal()
        yield session
    finally:
        # Clean up
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def app(test_db) -> FastAPI:
    """
    Create a FastAPI app for testing with DB dependency override.
    """
    from main import app as main_app
    
    # Override the get_db dependency to use the test database
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    main_app.dependency_overrides[get_db] = override_get_db
    
    return main_app


@pytest.fixture(scope="function")
def client(app, monkeypatch):
    """
    Create a test client for the FastAPI app with session patching.
    
    Uses the official FastAPI TestClient with patches for the session property.
    """
    from fastapi.testclient import TestClient
    from unittest.mock import PropertyMock
    
    # Create a custom property for Request.session that returns our session data
    session_data = {}
    
    # Set up session patching
    def patch_session(request):
        from fastapi import Request
        session_prop = PropertyMock(return_value=session_data)
        monkeypatch.setattr(Request, "session", session_prop)
    
    # Create a TestClient with the app
    test_client = TestClient(app)
    
    # Add a method to set session data
    def set_session(data):
        nonlocal session_data
        session_data.update(data)
        test_client.cookies.set("session", "test-session")
        return test_client
    
    # Patch session before each request
    original_request = test_client.request
    
    def patched_request(*args, **kwargs):
        patch_session(test_client)
        return original_request(*args, **kwargs)
    
    test_client.request = patched_request
    test_client.set_session = set_session
    
    return test_client


@pytest.fixture(scope="function")
def test_user(test_db) -> User:
    """
    Create a test user in the database.
    """
    user = User(
        id="test-user-id",
        username="test_user",
        display_name="Test User"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_twitter_account(test_db, test_user):
    """
    Create a test Twitter account linked to the test user.
    """
    # Import TwitterAccount here to avoid circular imports
    from plugins.twitter.models import TwitterAccount
    
    twitter_account = TwitterAccount(
        twitter_id="test-twitter-id",
        user_id=test_user.id,
        can_login=True
    )
    test_db.add(twitter_account)
    test_db.commit()
    test_db.refresh(twitter_account)
    return twitter_account


@pytest.fixture(scope="function")
def test_twitter_cookie_credentials(test_db, test_twitter_account):
    """
    Add cookie credentials to the test Twitter account.
    """
    test_twitter_account.twitter_cookie = "test-cookie-value"
    test_db.add(test_twitter_account)
    test_db.commit()
    test_db.refresh(test_twitter_account)
    return test_twitter_account


@pytest.fixture(scope="function")
def test_twitter_oauth_credentials(test_db, test_twitter_account):
    """
    Create test OAuth credentials for the test Twitter account.
    """
    # Import TwitterOAuthCredential here to avoid circular imports
    from plugins.twitter.models import TwitterOAuthCredential
    
    oauth_cred = TwitterOAuthCredential(
        twitter_account_id=test_twitter_account.twitter_id,
        oauth_token="test-oauth-token",
        oauth_token_secret="test-oauth-token-secret"
    )
    test_db.add(oauth_cred)
    test_db.commit()
    test_db.refresh(oauth_cred)
    return oauth_cred


@pytest.fixture
def mock_twitter_cookie_auth_plugin(monkeypatch):
    """
    Mock the TwitterCookieAuthorizationPlugin for testing.
    """
    class MockCookieAuthPlugin:
        service_name = "twitter_cookie"
        
        async def validate_credentials(self, credentials):
            return True
        
        async def get_user_identifier(self, credentials):
            return "test-twitter-id"
        
        def credentials_from_string(self, credentials_str):
            return {"cookie": credentials_str}
        
        def credentials_to_string(self, credentials):
            return credentials.get("cookie", "")
    
    # Monkeypatch the plugin_manager to return our mock plugin
    from plugin_manager import plugin_manager
    original_create_auth_plugin = plugin_manager.create_authorization_plugin
    
    def mock_create_authorization_plugin(service_name):
        if service_name == "twitter_cookie":
            return MockCookieAuthPlugin()
        return original_create_auth_plugin(service_name)
    
    monkeypatch.setattr(plugin_manager, "create_authorization_plugin", mock_create_authorization_plugin)
    
    return MockCookieAuthPlugin()


@pytest.fixture
def mock_twitter_oauth_auth_plugin(monkeypatch):
    """
    Mock the TwitterOAuthAuthorizationPlugin for testing.
    """
    class MockOAuthAuthPlugin:
        service_name = "twitter_oauth"
        
        async def validate_credentials(self, credentials):
            return True
        
        async def get_authorization_url(self, callback_url=None):
            return "https://twitter.com/oauth/authorize?oauth_token=test-request-token", {"oauth_token": "test-request-token"}
        
        async def process_callback(self, request_token, oauth_verifier):
            return {
                "oauth_token": "test-oauth-token",
                "oauth_token_secret": "test-oauth-token-secret",
                "user_id": "test-twitter-id",
                "screen_name": "test_twitter_user"
            }
        
        async def get_user_identifier(self, credentials):
            return credentials.get("user_id", "test-twitter-id")
        
        def credentials_from_string(self, credentials_str):
            import json
            return json.loads(credentials_str)
        
        def credentials_to_string(self, credentials):
            import json
            return json.dumps(credentials)
    
    # Monkeypatch the plugin_manager to return our mock plugin
    from plugin_manager import plugin_manager
    original_create_auth_plugin = plugin_manager.create_authorization_plugin
    
    def mock_create_authorization_plugin(service_name):
        if service_name == "twitter_oauth":
            return MockOAuthAuthPlugin()
        return original_create_auth_plugin(service_name)
    
    monkeypatch.setattr(plugin_manager, "create_authorization_plugin", mock_create_authorization_plugin)
    
    return MockOAuthAuthPlugin()


@pytest.fixture
def mock_twitter_resource_plugin(monkeypatch):
    """
    Mock the TwitterResourcePlugin for testing.
    """
    class MockClient:
        async def validate(self):
            return True
    
    class MockResourcePlugin:
        service_name = "twitter"
        
        SCOPES = {
            "tweet.post": "Permission to post tweets",
            "tweet.read": "Permission to read tweets",
            "tweet.delete": "Permission to delete tweets"
        }
        
        async def initialize_client(self, credentials):
            return MockClient()
        
        async def validate_client(self, client):
            return await client.validate()
        
        async def post_tweet(self, client, text):
            return "test-tweet-id"
    
    # Monkeypatch the plugin_manager to return our mock plugin
    from plugin_manager import plugin_manager
    original_create_resource_plugin = plugin_manager.create_resource_plugin
    
    def mock_create_resource_plugin(service_name):
        if service_name == "twitter":
            return MockResourcePlugin()
        return original_create_resource_plugin(service_name)
    
    monkeypatch.setattr(plugin_manager, "create_resource_plugin", mock_create_resource_plugin)
    
    return MockResourcePlugin()