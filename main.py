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

from models import User, WebAuthnCredential, TwitterAccount, PostKey, UserSession, TweetLog
from safety import SafetyFilter, SafetyLevel
from config import get_settings
from database import get_db, engine, Base
from twitter_client import TwitterClient

from patches import apply_patches
apply_patches()

app = FastAPI(title="OAuth3 Twitter Cookie Service")
templates = Jinja2Templates(directory="templates")

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

# Now import the router after middleware is set up
from webauthn_routes import router as webauthn_router
app.include_router(webauthn_router)

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
async def home(response: Response):
    return """
    <html>
        <head>
            <title>OAuth3 Twitter Cookie</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .auth-options {
                    display: flex;
                    gap: 20px;
                    margin-top: 20px;
                }
                .auth-option {
                    flex: 1;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                }
                .button {
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #0066cc;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-top: 10px;
                }
                .button:hover {
                    background-color: #0052a3;
                }
            </style>
        </head>
        <body>
            <h1>Welcome to OAuth3 Twitter Cookie</h1>
            <div class="auth-options">
                <div class="auth-option">
                    <h2>Register with Passkey</h2>
                    <p>Create a new account using your device's biometric authentication or security key.</p>
                    <a href="/register" class="button">Register with Passkey</a>
                </div>
                <div class="auth-option">
                    <h2>Login with Passkey</h2>
                    <p>Already have an account? Sign in with your passkey.</p>
                    <a href="/login" class="button">Login with Passkey</a>
                </div>
            </div>
        </body>
    </html>
    """

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("webauthn_register.html", {"request": request})

@app.get("/submit-cookie", response_class=HTMLResponse)
async def submit_cookie_page():
    return """
    <html>
        <head>
            <title>Submit Twitter Cookie</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }
                textarea {
                    width: 100%;
                    margin: 10px 0;
                }
                button {
                    background-color: #0066cc;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }
                button:hover {
                    background-color: #0052a3;
                }
            </style>
        </head>
        <body>
            <h1>Submit Twitter Cookie</h1>
            <form action="/api/cookie" method="POST" enctype="application/x-www-form-urlencoded">
                <textarea name="twitter_cookie" rows="10" cols="50" placeholder="Paste your Twitter cookie here"></textarea>
                <br>
                <button type="submit">Submit</button>
            </form>
        </body>
    </html>
    """

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("webauthn_login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        # Debug the session contents
        print("\n=== Dashboard Session Debug ===")
        print("Raw session:", request.session)
        print("Session as dict:", dict(request.session))
        print("user_id from session:", request.session.get("user_id"))
        print("user_id type:", type(request.session.get("user_id")))
        print("==============================\n")
        
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login")
        
        # Debug the database query
        user_query = db.query(User).filter(User.id == user_id)
        print("SQL Query:", str(user_query))
        
        user = user_query.first()
        print(f"User object: {user}")
        print(f"User type: {type(user)}")
        
        if not user:
            return RedirectResponse(url="/login")
        
        twitter_accounts = db.query(TwitterAccount).filter(
            TwitterAccount.user_id == user_id
        ).all()
        
        post_keys = []
        for account in twitter_accounts:
            keys = db.query(PostKey).filter(
                PostKey.twitter_id == account.twitter_id,
                PostKey.is_active == True
            ).all()
            post_keys.extend(keys)
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": user,
                "twitter_accounts": twitter_accounts,
                "post_keys": post_keys
            }
        )
    except Exception as e:
        print(f"Error in dashboard: {e}\nTraceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

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
        return {"status": "success", "message": "Twitter account linked successfully"}
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}\nTraceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Invalid cookie format: {str(e)}")
    except Exception as e:
        print(f"Error in submit_cookie: {e}\nTraceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/keys")
async def create_post_key(
    name: str = Form(...),
    session: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_session = db.query(UserSession).filter(
        UserSession.session_token == session,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    
    if not user_session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Check if max keys reached
    key_count = db.query(PostKey).filter(
        PostKey.twitter_id == user_session.twitter_id,
        PostKey.is_active == True
    ).count()
    
    if key_count >= settings.POST_KEY_MAX_PER_ACCOUNT:
        raise HTTPException(status_code=400, detail="Maximum number of post keys reached")
    
    post_key = PostKey(
        twitter_id=user_session.twitter_id,
        name=name
    )
    db.add(post_key)
    db.commit()
    
    return {"status": "success", "key_id": post_key.key_id}

@app.delete("/api/keys/{key_id}")
async def revoke_post_key(
    key_id: str,
    session: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_session = db.query(UserSession).filter(
        UserSession.session_token == session,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    
    if not user_session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    post_key = db.query(PostKey).filter(
        PostKey.key_id == key_id,
        PostKey.twitter_id == user_session.twitter_id
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
        
        return {"status": "success", "tweet_id": tweet_id}
        
    except Exception as e:
        print(f"Error in post_tweet: {e}\nTraceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# Add this after creating the FastAPI app
@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        import traceback
        print(f"\n\n*** Exception in request: {request.url}")
        print(f"*** {e.__class__.__name__}: {str(e)}")
        print("*** Traceback:")
        print(traceback.format_exc())
        print("\n")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=1,  # Single worker
        log_level="debug",
        reload=True,  # Enable auto-reload
        use_colors=True
    ) 