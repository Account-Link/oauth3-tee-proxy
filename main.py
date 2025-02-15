from fastapi import FastAPI, HTTPException, Depends, Cookie, Response, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
from typing import Optional
from pydantic import BaseModel
import json
import traceback

from models import Base, TwitterAccount, PostKey, UserSession, TweetLog
from safety import SafetyFilter, SafetyLevel
from config import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from twitter_client import TwitterClient

from patches import apply_patches
apply_patches()

app = FastAPI(title="OAuth3 Twitter Cookie Service")
templates = Jinja2Templates(directory="templates")

# Database setup
settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
            <title>Twitter Cookie Management</title>
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

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(session: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_session = db.query(UserSession).filter(
        UserSession.session_token == session,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    
    if not user_session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    post_keys = db.query(PostKey).filter(
        PostKey.twitter_id == user_session.twitter_id,
        PostKey.is_active == True
    ).all()
    
    return f"""
    <html>
        <head>
            <title>Post Keys Dashboard</title>
        </head>
        <body>
            <h1>Post Keys</h1>
            <h2>Create New Post Key</h2>
            <form action="/api/keys" method="POST">
                <input type="text" name="name" placeholder="Key Name">
                <button type="submit">Create</button>
            </form>
            
            <h2>Existing Keys</h2>
            <ul>
                {"".join(f'<li>{key.name} ({key.key_id}) <form action="/api/keys/{key.key_id}" method="POST" style="display:inline"><button type="submit">Revoke</button></form></li>' for key in post_keys)}
            </ul>
        </body>
    </html>
    """

# API Routes (for curl/programmatic access)
@app.post("/api/cookie")
async def submit_cookie(
    response: Response,
    db: Session = Depends(get_db),
    twitter_cookie: str = Form(...)
):
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
            existing_account.twitter_cookie = twitter_cookie
            existing_account.updated_at = datetime.utcnow()
        else:
            account = TwitterAccount(
                twitter_id=twitter_id,
                twitter_cookie=twitter_cookie
            )
            db.add(account)
        
        # Create session
        session_token = str(uuid.uuid4())
        session = UserSession(
            twitter_id=twitter_id,
            session_token=session_token,
            expires_at=datetime.utcnow() + timedelta(hours=settings.SESSION_EXPIRY_HOURS)
        )
        db.add(session)
        db.commit()
        
        response.set_cookie(key="session", value=session_token)
        return {"status": "success", "message": "Cookie stored successfully"}
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
                # Log the attempt
                log_entry = TweetLog(
                    post_key_id=post_key.key_id,
                    tweet_text=tweet_data.text,
                    safety_check_result=False,
                    safety_check_message=reason
                )
                db.add(log_entry)
                db.commit()
                
                raise HTTPException(status_code=400, detail=f"Safety check failed: {reason}")
        
        # Create Twitter client and post tweet
        client = TwitterClient.from_cookie_string(twitter_account.twitter_cookie)
        tweet_id = await client.post_tweet(tweet_data.text)
        
        # Log the successful attempt
        log_entry = TweetLog(
            post_key_id=post_key.key_id,
            tweet_text=tweet_data.text,
            safety_check_result=True
        )
        db.add(log_entry)
        db.commit()
        
        return {
            "status": "success",
            "message": "Tweet posted successfully",
            "tweet_id": tweet_id
        }
    except Exception as e:
        print(f"Error in post_tweet: {e}\nTraceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 