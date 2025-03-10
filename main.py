# Standard library imports
import json
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
    Response, 
    Form, 
    Request, 
    Security
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
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
    TweetLog, 
    TelegramAccount, 
    TelegramChannel
)
from oauth2_routes import (
    OAuth2Token,
    router as oauth2_router, 
    verify_token_and_scopes
)
from safety import SafetyFilter, SafetyLevel

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
from telegram_routes import router as telegram_router
from oauth2_routes import router as oauth2_router, update_scopes_from_plugins

# Initialize plugins first
plugin_manager.discover_plugins()

# Update OAuth2 scopes from plugins
update_scopes_from_plugins()

# Now include routers
app.include_router(webauthn_router)
app.include_router(telegram_router)
app.include_router(oauth2_router)

# Pydantic models
class TwitterCookieSubmit(BaseModel):
    """Model for submitting Twitter cookie."""
    twitter_cookie: str

class TweetRequest(BaseModel):
    """Model for tweet requests."""
    text: str
    bypass_safety: bool = False

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

# API Routes (for curl/programmatic access)
@app.post("/api/cookie")
async def submit_cookie(
    response: Response,
    db: Session = Depends(get_db),
    twitter_cookie: str = Form(...),
    request: Request = None
):
    """
    Submit and validate a Twitter cookie.
    Links the Twitter account to the authenticated user.
    """
    if not request.session.get("user_id"):
        raise HTTPException(
            status_code=401, 
            detail="Authentication required. Please log in first."
        )
    
    try:
        # Get the Twitter auth plugin
        twitter_auth = plugin_manager.create_authorization_plugin("twitter")
        if not twitter_auth:
            raise HTTPException(
                status_code=500,
                detail="Twitter plugin not available"
            )
        
        # Parse and validate the cookie
        credentials = twitter_auth.credentials_from_string(twitter_cookie)
        if not await twitter_auth.validate_credentials(credentials):
            raise HTTPException(
                status_code=400, 
                detail="Invalid Twitter cookie. Please provide a valid cookie."
            )
        
        # Get Twitter ID from the cookie
        twitter_id = await twitter_auth.get_user_identifier(credentials)
        
        # Check if account already exists
        existing_account = db.query(TwitterAccount).filter(
            TwitterAccount.twitter_id == twitter_id
        ).first()
        
        if existing_account:
            if existing_account.user_id and existing_account.user_id != request.session.get("user_id"):
                raise HTTPException(status_code=400, detail="Twitter account already linked to another user")
            existing_account.twitter_cookie = twitter_cookie
            existing_account.updated_at = datetime.utcnow()
            existing_account.user_id = request.session.get("user_id")
        else:
            account = TwitterAccount(
                twitter_id=twitter_id,
                twitter_cookie=twitter_cookie,
                user_id=request.session.get("user_id")
            )
            db.add(account)
        
        db.commit()
        logger.info(f"Successfully linked Twitter account {twitter_id} to user {request.session.get('user_id')}")
        return {"status": "success", "message": "Twitter account linked successfully"}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid cookie format: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail="Invalid cookie format. Please check the cookie structure."
        )
    except Exception as e:
        logger.error(f"Error processing cookie submission: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred while processing your request."
        )

@app.post("/api/tweet")
async def post_tweet(
    tweet_data: TweetRequest,
    token: OAuth2Token = Security(verify_token_and_scopes, scopes=["tweet.post"]),
    db: Session = Depends(get_db)
):
    try:
        twitter_account = db.query(TwitterAccount).filter(
            TwitterAccount.user_id == token.user_id
        ).first()
        
        if not twitter_account:
            logger.error(f"No Twitter account found for user {token.user_id}")
            raise HTTPException(status_code=404, detail="Twitter account not found")
        
        # Safety check
        if settings.SAFETY_FILTER_ENABLED and not tweet_data.bypass_safety:
            safety_filter = SafetyFilter(level=SafetyLevel.MODERATE)
            is_safe, reason = await safety_filter.check_tweet(tweet_data.text)
            
            if not is_safe:
                await log_failed_tweet(db, token.user_id, tweet_data.text, reason)
                raise HTTPException(status_code=400, detail=f"Tweet failed safety check: {reason}")
        
        # Get plugins
        twitter_auth = plugin_manager.create_authorization_plugin("twitter")
        twitter_resource = plugin_manager.create_resource_plugin("twitter")
        
        if not twitter_auth or not twitter_resource:
            raise HTTPException(
                status_code=500,
                detail="Twitter plugins not available"
            )
        
        # Get credentials and initialize client
        credentials = twitter_auth.credentials_from_string(twitter_account.twitter_cookie)
        client = await twitter_resource.initialize_client(credentials)
        
        # Post tweet
        tweet_id = await twitter_resource.post_tweet(client, tweet_data.text)
        
        # Log successful tweet
        await log_successful_tweet(db, token.user_id, tweet_data.text, tweet_id)
        
        return {"status": "success", "tweet_id": tweet_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error posting tweet for user {token.user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

async def log_failed_tweet(db: Session, user_id: str, tweet_text: str, reason: str):
    """Log a failed tweet attempt."""
    tweet_log = TweetLog(
        user_id=user_id,
        tweet_text=tweet_text,
        safety_check_result=False,
        safety_check_message=reason
    )
    db.add(tweet_log)
    db.commit()
    logger.warning(f"Tweet failed safety check for user {user_id}: {reason}")

async def log_successful_tweet(db: Session, user_id: str, tweet_text: str, tweet_id: str):
    """Log a successful tweet."""
    tweet_log = TweetLog(
        user_id=user_id,
        tweet_text=tweet_text,
        safety_check_result=True,
        tweet_id=tweet_id
    )
    db.add(tweet_log)
    db.commit()
    logger.info(f"Successfully posted tweet {tweet_id} for user {user_id}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        use_colors=True
    ) 