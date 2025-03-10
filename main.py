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
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

# Local imports
from config import get_settings
from database import get_db, engine, Base
from models import (
    User, 
    WebAuthnCredential, 
    TwitterAccount, 
    UserSession, 
    TelegramAccount, 
    TelegramChannel
)
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
templates = Jinja2Templates(directory="templates")

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
from webauthn_routes import router as webauthn_router
from oauth2_routes import router as oauth2_router, update_scopes_from_plugins

# Initialize plugins first
plugin_manager.discover_plugins()

# Update OAuth2 scopes from plugins
update_scopes_from_plugins()

# Now include routers
app.include_router(webauthn_router)
app.include_router(oauth2_router)

# Include service-specific routers from plugins
service_routers = plugin_manager.get_service_routers()
for service_name, router in service_routers.items():
    app.include_router(router, prefix=f"/{service_name}")
    logger.info(f"Mounted routes for service: {service_name}")

# Routes for web interface (browser-based)
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("webauthn_register.html", {"request": request})

@app.get("/submit-cookie", response_class=HTMLResponse)
async def submit_cookie_page(request: Request):
    return templates.TemplateResponse("submit_cookie.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("webauthn_login.html", {"request": request})

@app.get("/add-telegram", response_class=HTMLResponse)
async def add_telegram_page(request: Request):
    # Check if user is authenticated
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("add_telegram.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login")
    
    twitter_accounts = db.query(TwitterAccount).filter(
        TwitterAccount.user_id == user_id
    ).all()
    
    telegram_accounts = db.query(TelegramAccount).filter(
        TelegramAccount.user_id == user_id
    ).all()
    
    # Get channels for each Telegram account
    for account in telegram_accounts:
        account.channels = db.query(TelegramChannel).filter(
            TelegramChannel.telegram_account_id == account.id
        ).all()
    
    # Get active OAuth2 tokens
    oauth2_tokens = db.query(OAuth2Token).filter(
        OAuth2Token.user_id == user_id,
        OAuth2Token.is_active == True,
        OAuth2Token.expires_at > datetime.utcnow()
    ).all()
    
    # Get all available scopes from plugins
    available_scopes = plugin_manager.get_all_plugin_scopes()
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "twitter_accounts": twitter_accounts,
            "telegram_accounts": telegram_accounts,
            "oauth2_tokens": oauth2_tokens,
            "available_scopes": available_scopes.keys()
        }
    )

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