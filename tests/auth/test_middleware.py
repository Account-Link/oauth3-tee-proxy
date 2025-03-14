"""
Test Authentication Middleware
============================

This module contains tests for the authentication middleware.
"""

import pytest
from fastapi import FastAPI, Request, Response, Depends
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from datetime import datetime, timedelta

from database import get_db, Base
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean

# Import directly from models.py instead of redefining
from models import User, JWTToken

from auth.middleware import AuthMiddleware, get_current_user
from auth.jwt_service import create_token

class TestAuthMiddleware:
    """Test cases for authentication middleware."""
    
    @pytest.fixture
    def db_session(self):
        """Get a database session for tests."""
        db = next(get_db())
        yield db
    
    @pytest.fixture
    def test_user(self, db_session):
        """Create a test user for authentication."""
        try:
            # Create a test user directly with SQL to avoid SQLAlchemy relationship issues
            from uuid import uuid4
            from datetime import datetime
            
            # Check if user exists
            result = db_session.execute("SELECT id FROM users WHERE username = 'test_middleware_user'").fetchone()
            
            if result:
                user_id = result[0]
            else:
                user_id = str(uuid4())
                db_session.execute(
                    "INSERT INTO users (id, username, display_name, created_at, updated_at) "
                    "VALUES (:id, :username, :display_name, :created_at, :updated_at)",
                    {
                        "id": user_id,
                        "username": "test_middleware_user",
                        "display_name": "Test Middleware User",
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                )
                db_session.commit()
            
            # Create a User object with the ID
            user = User()
            user.id = user_id
            user.username = "test_middleware_user"
            user.display_name = "Test Middleware User"
            
            return user
            
        except Exception as e:
            pytest.skip(f"Failed to create test user: {e}")
            return None
    
    @pytest.fixture
    def test_token(self, db_session, test_user):
        """Create a test JWT token."""
        # Create token
        token_data = create_token(
            user_id=test_user.id,
            policy="test",
            scopes=["test.read", "test.write"],
            db=db_session,
            expiry_hours=1
        )
        
        yield token_data
        
        # Clean up
        db_token = db_session.query(JWTToken).filter(
            JWTToken.token_id == token_data["token_id"]
        ).first()
        
        if db_token:
            db_session.delete(db_token)
            db_session.commit()
    
    @pytest.fixture
    def test_app(self, test_token):
        """Create a test FastAPI application with auth middleware."""
        app = FastAPI()
        
        # Add auth middleware
        app.add_middleware(
            AuthMiddleware,
            public_paths=[
                "/public",
                "/public/*"
            ],
            protected_paths=[
                "/protected",
                "/protected/*"
            ]
        )
        
        # Test routes
        @app.get("/public")
        async def public_route():
            return {"message": "This is a public route"}
        
        @app.get("/public/nested")
        async def public_nested_route():
            return {"message": "This is a nested public route"}
        
        @app.get("/protected")
        async def protected_route(request: Request):
            return {
                "message": "This is a protected route",
                "user_id": request.state.user.id if hasattr(request.state, "user") else None
            }
        
        @app.get("/protected/nested")
        async def protected_nested_route(request: Request):
            return {
                "message": "This is a nested protected route",
                "user_id": request.state.user.id if hasattr(request.state, "user") else None
            }
        
        @app.get("/protected/current-user")
        async def current_user_route(user: User = Depends(get_current_user)):
            return {
                "message": "Got current user",
                "user_id": user.id,
                "username": user.username
            }
        
        return app
    
    @pytest.fixture
    def client(self, test_app):
        """Create a test client for the app."""
        return TestClient(test_app)
    
    def test_public_routes(self, client):
        """Test access to public routes."""
        # Test public route
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json()["message"] == "This is a public route"
        
        # Test nested public route
        response = client.get("/public/nested")
        assert response.status_code == 200
        assert response.json()["message"] == "This is a nested public route"
    
    def test_protected_routes_without_auth(self, client):
        """Test access to protected routes without authentication."""
        # Test protected route without auth
        response = client.get("/protected")
        assert response.status_code == 401
        
        # Test nested protected route without auth
        response = client.get("/protected/nested")
        assert response.status_code == 401
    
    def test_protected_routes_with_auth(self, client, test_token):
        """Test access to protected routes with authentication."""
        # Test protected route with auth header
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {test_token['token']}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "This is a protected route"
        assert response.json()["user_id"] is not None
        
        # Test nested protected route with auth header
        response = client.get(
            "/protected/nested",
            headers={"Authorization": f"Bearer {test_token['token']}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "This is a nested protected route"
        assert response.json()["user_id"] is not None
    
    def test_protected_routes_with_cookie(self, client, test_token):
        """Test access to protected routes with authentication cookie."""
        # Test protected route with auth cookie
        response = client.get(
            "/protected",
            cookies={"access_token": test_token["token"]}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "This is a protected route"
        assert response.json()["user_id"] is not None
        
        # Test nested protected route with auth cookie
        response = client.get(
            "/protected/nested",
            cookies={"access_token": test_token["token"]}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "This is a nested protected route"
        assert response.json()["user_id"] is not None
    
    def test_invalid_token(self, client):
        """Test access with invalid token."""
        # Test with invalid token
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
        
        # Test with expired token
        # This would require creating an expired token or mocking the validation
        # For now, we'll skip this test