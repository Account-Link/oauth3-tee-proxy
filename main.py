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
from models import User, WebAuthnCredential, OAuth2Token
from oauth2_routes import router as oauth2_router

# Plugin system
from plugin_manager import plugin_manager

# Apply patches
from patches import apply_patches
apply_patches()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
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

# Add session middleware FIRST
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY,
    session_cookie="oauth3_session",
    max_age=settings.SESSION_EXPIRY_HOURS * 3600,
    same_site="lax",
    https_only=False
)

# Import and include routers
from oauth2_routes import router as oauth2_router, update_scopes_from_plugins
from ui_routes import router as ui_router

# Initialize plugins first
plugin_manager.discover_plugins()

# Update OAuth2 scopes from plugins
update_scopes_from_plugins()

# Now include routers
app.include_router(oauth2_router)
app.include_router(ui_router)

# Include service-specific routers from plugins
service_routers = plugin_manager.get_service_routers()
for service_name, router in service_routers.items():
    app.include_router(router, prefix=f"/{service_name}")
    logger.info(f"Mounted routes for service: {service_name}")

# API routes are now provided by service-specific plugins

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        use_colors=True
    ) 