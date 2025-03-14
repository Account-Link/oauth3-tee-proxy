# Standard library imports
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Third-party imports
from fastapi import (
    FastAPI, 
    HTTPException, 
    Depends, 
    Cookie, 
    Request
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

# Local imports
from config import get_settings
from database import get_db, engine, Base
from models import User, WebAuthnCredential, JWTToken
from auth.middleware import AuthMiddleware

# Plugin system
from plugin_manager import plugin_manager

# Apply patches
from patches import apply_patches
apply_patches()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="OAuth3 TEE Proxy")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Get settings
settings = get_settings()

# Initialize database
Base.metadata.create_all(bind=engine)

# Add session middleware FIRST (needed for WebAuthn)
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY,
    session_cookie="oauth3_session",
    max_age=settings.SESSION_EXPIRY_HOURS * 3600,
    same_site="lax",
    https_only=False
)

# Add authentication middleware
app.add_middleware(
    AuthMiddleware,
    public_paths=[
        "/",
        "/auth/register",
        "/auth/register/begin",
        "/auth/register/complete",
        "/auth/login",
        "/auth/login/begin",
        "/auth/login/complete",
        "/auth/logout",
        "/static/*",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/webauthn/*"  # Legacy WebAuthn endpoints implement their own authentication
    ],
    protected_paths=[
        "/profile",
        "/profile/*",
        "/auth/profile",
        "/auth/profile/*",
        "/auth/passkeys/*",
        "/auth/tokens/*",
        "/api/*",
        "/dashboard",
        "/dashboard/*"
    ]
)

# Import and include routers
from ui_routes.auth_routes import router as auth_router
from ui_routes.dashboard_routes import router as dashboard_router
from ui_routes.api_routes import router as api_router, update_available_scopes
from ui_routes.webauthn_routes import router as webauthn_router

# Initialize plugins first
plugin_manager.discover_plugins()

# Get plugin scopes and update API router
plugin_scopes = plugin_manager.get_all_plugin_scopes()
update_available_scopes(plugin_scopes)

# Register routers
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(api_router)
app.include_router(webauthn_router)

# Root route
@app.get("/")
async def root(request: Request):
    """Render the home page."""
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="templates")
    
    # Check if user is authenticated
    user = getattr(request.state, "user", None)
    
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "title": "OAuth3 TEE Proxy",
            "user": user
        }
    )

# Profile redirect route
@app.get("/profile")
async def profile_redirect():
    """Redirect to the auth profile page."""
    return RedirectResponse(url="/auth/profile", status_code=303)

# Include service-specific routers from plugins
service_routers = plugin_manager.get_service_routers()
for service_name, router in service_routers.items():
    app.include_router(router, prefix=f"/{service_name}")
    logger.info(f"Mounted routes for service: {service_name}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        use_colors=True
    ) 