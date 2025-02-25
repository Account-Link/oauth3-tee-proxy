from fastapi import FastAPI, HTTPException, Depends, Cookie, Response, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timedelta
import uuid
from typing import Optional
from pydantic import BaseModel
import json
import traceback
import logging

from models import User, WebAuthnCredential, TwitterAccount, PostKey, UserSession, TweetLog, TelegramAccount, TelegramChannel
from safety import SafetyFilter, SafetyLevel
from config import get_settings
from database import get_db, engine, Base
from twitter_client import TwitterClient

from patches import apply_patches
apply_patches()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="OAuth3 Twitter Cookie Service")
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

app.include_router(webauthn_router)
app.include_router(telegram_router)

# Pydantic models
class TwitterCookieSubmit(BaseModel):
    twitter_cookie: str

class PostKeyCreate(BaseModel):
    name: str

class TweetRequest(BaseModel):
    post_key: str
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
    
    post_keys = db.query(PostKey).filter(
        PostKey.user_id == user_id,
        PostKey.is_active == True
    ).all()
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "twitter_accounts": twitter_accounts,
            "telegram_accounts": telegram_accounts,
            "post_keys": post_keys
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
    # Check if user is authenticated
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Create Twitter client and validate cookie
        client = TwitterClient.from_cookie_string(twitter_cookie)
        if not await client.validate_cookie():
            raise HTTPException(status_code=400, detail="Invalid Twitter cookie")
        
        # Get Twitter ID from the cookie
        twitter_id = await client.get_user_id()
        
        # Check if account already exists
        existing_account = db.query(TwitterAccount).filter(
            TwitterAccount.twitter_id == twitter_id
        ).first()
        
        if existing_account:
            if existing_account.user_id and existing_account.user_id != user_id:
                raise HTTPException(status_code=400, detail="Twitter account already linked to another user")
            existing_account.twitter_cookie = twitter_cookie
            existing_account.updated_at = datetime.utcnow()
            existing_account.user_id = user_id
        else:
            account = TwitterAccount(
                twitter_id=twitter_id,
                twitter_cookie=twitter_cookie,
                user_id=user_id
            )
            db.add(account)
        
        db.commit()
        logger.info(f"Successfully linked Twitter account {twitter_id} to user {user_id}")
        return {"status": "success", "message": "Twitter account linked successfully"}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error while processing cookie: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid cookie format: {str(e)}")
    except Exception as e:
        logger.error(f"Error in submit_cookie: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/keys")
async def create_post_key(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if user is authenticated via session
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user's Twitter accounts
    twitter_accounts = db.query(TwitterAccount).filter(
        TwitterAccount.user_id == user_id
    ).first()
    
    if not twitter_accounts:
        raise HTTPException(status_code=400, detail="No Twitter account linked")

    # Check if max keys reached
    key_count = db.query(PostKey).filter(
        PostKey.twitter_id == twitter_accounts.twitter_id,
        PostKey.is_active == True
    ).count()
    
    if key_count >= settings.POST_KEY_MAX_PER_ACCOUNT:
        raise HTTPException(status_code=400, detail="Maximum number of post keys reached")
    
    post_key = PostKey(
        twitter_id=twitter_accounts.twitter_id,
        name=name
    )
    db.add(post_key)
    db.commit()
    
    return {"status": "success", "key_id": post_key.key_id}

@app.delete("/api/keys/{key_id}")
async def revoke_post_key(
    key_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    # Check if user is authenticated via session
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user's Twitter accounts
    twitter_account = db.query(TwitterAccount).filter(
        TwitterAccount.user_id == user_id
    ).first()
    
    if not twitter_account:
        raise HTTPException(status_code=400, detail="No Twitter account linked")
    
    post_key = db.query(PostKey).filter(
        PostKey.key_id == key_id,
        PostKey.twitter_id == twitter_account.twitter_id
    ).first()
    
    if not post_key:
        raise HTTPException(status_code=404, detail="Post key not found")
    
    post_key.is_active = False
    db.commit()
    
    return {"status": "success", "message": "Post key revoked"}

@app.post("/api/tweet")
async def post_tweet(
    tweet_data: TweetRequest,
    db: Session = Depends(get_db)
):
    try:
        post_key = db.query(PostKey).filter(
            PostKey.key_id == tweet_data.post_key,
            PostKey.is_active == True
        ).first()
        
        if not post_key:
            raise HTTPException(status_code=404, detail="Invalid or inactive post key")
        
        # Get the associated Twitter account
        twitter_account = db.query(TwitterAccount).filter(
            TwitterAccount.twitter_id == post_key.twitter_id
        ).first()
        
        if not twitter_account:
            raise HTTPException(status_code=404, detail="Twitter account not found")
        
        # Safety check
        if settings.SAFETY_FILTER_ENABLED and not (post_key.can_bypass_safety and tweet_data.bypass_safety):
            safety_filter = SafetyFilter(level=SafetyLevel(post_key.safety_level))
            is_safe, reason = await safety_filter.check_tweet(tweet_data.text)
            
            if not is_safe:
                # Log the safety check failure
                tweet_log = TweetLog(
                    post_key_id=post_key.key_id,
                    tweet_text=tweet_data.text,
                    safety_check_result=False,
                    safety_check_message=reason
                )
                db.add(tweet_log)
                db.commit()
                
                logger.warning(f"Tweet failed safety check for post_key {post_key.key_id}: {reason}")
                raise HTTPException(status_code=400, detail=f"Tweet failed safety check: {reason}")
        
        # Create Twitter client
        client = TwitterClient.from_cookie_string(twitter_account.twitter_cookie)
        
        # Post tweet
        tweet_id = await client.post_tweet(tweet_data.text)
        
        # Log successful tweet
        tweet_log = TweetLog(
            post_key_id=post_key.key_id,
            tweet_text=tweet_data.text,
            safety_check_result=True
        )
        db.add(tweet_log)
        db.commit()
        
        logger.info(f"Successfully posted tweet {tweet_id} using post_key {post_key.key_id}")
        return {"status": "success", "tweet_id": tweet_id}
        
    except Exception as e:
        logger.error(f"Error in post_tweet: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        use_colors=True
    ) 