from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException, Security
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import User, TwitterAccount, TwitterOAuthCredential, OAuth2Token, OAuth2Request, TweetLog
import uuid
from datetime import datetime, timedelta
import secrets
import twitter_oauth
import logging
from pydantic import BaseModel
from oauth2_routes import verify_token_and_scopes  # Import the function from oauth2_routes

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Define tweet request model
class OAuth1TweetRequest(BaseModel):
    """Model for OAuth1-based tweet requests."""
    text: str
    bypass_safety: bool = False

@router.get("/auth/twitter/login")
async def twitter_login(request: Request, next: str = Query(None), request_id: str = Query(None)):
    """Initiate Twitter OAuth login."""
    try:
        redirect_url, request_token = twitter_oauth.get_authorization_url()
        
        # Store request token in session
        request.session["twitter_request_token"] = request_token
        request.session["twitter_auth_flow"] = "login"
        
        # Store next URL if provided
        if next:
            request.session["twitter_auth_next"] = next
        
        # If this is part of an OAuth flow, store the request_id
        if request_id:
            request.session["pending_oauth_request_id"] = request_id
        
        return RedirectResponse(redirect_url)
    except Exception as e:
        logger.error(f"Error initiating Twitter login: {str(e)}")
        raise HTTPException(status_code=500, detail="Error initiating Twitter login")

@router.get("/auth/twitter/callback")
async def twitter_callback(
    request: Request,
    oauth_token: str = Query(None),
    oauth_verifier: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handle Twitter OAuth callback."""
    if not oauth_token or not oauth_verifier:
        raise HTTPException(status_code=400, detail="Missing OAuth parameters")
    
    # Get request token from session
    request_token = request.session.get("twitter_request_token")
    if not request_token:
        raise HTTPException(status_code=400, detail="Invalid session state")
    
    # Get access token
    try:
        access_token, access_token_secret = twitter_oauth.get_access_token(request_token, oauth_verifier)
    except ValueError as e:
        logger.error(f"Error getting access token: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get Twitter user info
    try:
        twitter_user = twitter_oauth.get_twitter_user_info(access_token, access_token_secret)
        twitter_id = twitter_user["id"]
    except Exception as e:
        logger.error(f"Error getting Twitter user info: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to get Twitter user info")
    
    # Check if this is a login flow
    auth_flow = request.session.get("twitter_auth_flow", "")
    
    # Get next URL if available
    next_url = request.session.get("twitter_auth_next", "/dashboard")
    
    # Check if Twitter account exists
    twitter_account = db.query(TwitterAccount).filter(TwitterAccount.twitter_id == twitter_id).first()
    
    # Determine if this is part of an OAuth authorization flow
    pending_oauth_request_id = request.session.get("pending_oauth_request_id")
    
    if twitter_account:
        # Twitter account exists
        if auth_flow == "login" and twitter_account.can_login:
            # Set session for this user
            request.session["user_id"] = twitter_account.user_id
            
            # Update or create OAuth credentials
            oauth_cred = db.query(TwitterOAuthCredential).filter(
                TwitterOAuthCredential.twitter_account_id == twitter_id
            ).first()
            
            if oauth_cred:
                oauth_cred.oauth_token = access_token
                oauth_cred.oauth_token_secret = access_token_secret
                oauth_cred.updated_at = datetime.utcnow()
            else:
                oauth_cred = TwitterOAuthCredential(
                    twitter_account_id=twitter_id,
                    oauth_token=access_token,
                    oauth_token_secret=access_token_secret
                )
                db.add(oauth_cred)
            
            db.commit()
            
            # Clear the session variables related to Twitter auth
            if "twitter_request_token" in request.session:
                del request.session["twitter_request_token"]
            if "twitter_auth_flow" in request.session:
                del request.session["twitter_auth_flow"]
            if "twitter_auth_next" in request.session:
                del request.session["twitter_auth_next"]
            
            # If this is part of an OAuth flow, redirect to the authorize page
            if pending_oauth_request_id:
                oauth_redirect = f"/oauth/authorize?request_id={pending_oauth_request_id}"
                # Keep the pending_oauth_request_id in session - we'll remove it after the authorization
                return RedirectResponse(oauth_redirect, status_code=303)
                
            return RedirectResponse(next_url, status_code=303)
        elif auth_flow == "link":
            # Linking to existing user
            user_id = request.session.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            # Update Twitter account user_id if not already set
            if twitter_account.user_id != user_id:
                twitter_account.user_id = user_id
            
            # Store OAuth credentials
            oauth_cred = db.query(TwitterOAuthCredential).filter(
                TwitterOAuthCredential.twitter_account_id == twitter_id
            ).first()
            
            if oauth_cred:
                oauth_cred.oauth_token = access_token
                oauth_cred.oauth_token_secret = access_token_secret
                oauth_cred.updated_at = datetime.utcnow()
            else:
                oauth_cred = TwitterOAuthCredential(
                    twitter_account_id=twitter_id,
                    oauth_token=access_token,
                    oauth_token_secret=access_token_secret
                )
                db.add(oauth_cred)
            
            db.commit()
            
            # Clear the session variables related to Twitter auth
            if "twitter_request_token" in request.session:
                del request.session["twitter_request_token"]
            if "twitter_auth_flow" in request.session:
                del request.session["twitter_auth_flow"]
            if "twitter_auth_next" in request.session:
                del request.session["twitter_auth_next"]
            
            # If this is part of an OAuth flow, redirect to the authorize page
            if pending_oauth_request_id:
                oauth_redirect = f"/oauth/authorize?request_id={pending_oauth_request_id}"
                del request.session["pending_oauth_request_id"]
                return RedirectResponse(oauth_redirect, status_code=303)
                
            return RedirectResponse(next_url, status_code=303)
    else:
        # Twitter account doesn't exist
        if auth_flow == "login":
            # Create new user and Twitter account
            user_id = str(uuid.uuid4())
            username = f"twitter_{twitter_user['screen_name']}"
            
            # Create user
            user = User(
                id=user_id,
                username=username,
                display_name=twitter_user["name"]
            )
            db.add(user)
            
            # Create Twitter account
            twitter_account = TwitterAccount(
                twitter_id=twitter_id,
                user_id=user_id,
                twitter_cookie="",  # Empty as we're using OAuth
                can_login=True
            )
            db.add(twitter_account)
            
            # Store OAuth credentials
            oauth_cred = TwitterOAuthCredential(
                twitter_account_id=twitter_id,
                oauth_token=access_token,
                oauth_token_secret=access_token_secret
            )
            db.add(oauth_cred)
            db.commit()
            
            # Set session
            request.session["user_id"] = user_id
            
            # Clear the session variables related to Twitter auth
            if "twitter_request_token" in request.session:
                del request.session["twitter_request_token"]
            if "twitter_auth_flow" in request.session:
                del request.session["twitter_auth_flow"]
            if "twitter_auth_next" in request.session:
                del request.session["twitter_auth_next"]
            
            # If this is part of an OAuth flow, redirect to the authorize page
            if pending_oauth_request_id:
                oauth_redirect = f"/oauth/authorize?request_id={pending_oauth_request_id}"
                del request.session["pending_oauth_request_id"]
                return RedirectResponse(oauth_redirect, status_code=303)
                
            return RedirectResponse(next_url, status_code=303)
        elif auth_flow == "link":
            # Linking to existing user
            user_id = request.session.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            # Create Twitter account
            twitter_account = TwitterAccount(
                twitter_id=twitter_id,
                user_id=user_id,
                twitter_cookie="",  # Empty as we're using OAuth
                can_login=True
            )
            db.add(twitter_account)
            
            # Store OAuth credentials
            oauth_cred = TwitterOAuthCredential(
                twitter_account_id=twitter_id,
                oauth_token=access_token,
                oauth_token_secret=access_token_secret
            )
            db.add(oauth_cred)
            db.commit()
            
            # Clear the session variables related to Twitter auth
            if "twitter_request_token" in request.session:
                del request.session["twitter_request_token"]
            if "twitter_auth_flow" in request.session:
                del request.session["twitter_auth_flow"]
            if "twitter_auth_next" in request.session:
                del request.session["twitter_auth_next"]
            
            # If this is part of an OAuth flow, redirect to the authorize page
            if pending_oauth_request_id:
                oauth_redirect = f"/oauth/authorize?request_id={pending_oauth_request_id}"
                del request.session["pending_oauth_request_id"]
                return RedirectResponse(oauth_redirect, status_code=303)
                
            return RedirectResponse(next_url, status_code=303)
    
    # Default fallback
    return RedirectResponse("/", status_code=303)

@router.get("/oauth/get_auth_redirect")
async def get_auth_redirect(
    request: Request,
    callback_url: str = Query(...),
    scope: str = Query(...),
    state: str = Query(None),
    db: Session = Depends(get_db)
):
    """Generate authorization URL for third-party apps."""
    # Check if scope is valid
    if scope != "twitter_oauth1.auth" and scope != "twitter_oauth1.tweet":
        raise HTTPException(status_code=400, detail="Invalid scope")
    
    # Generate a request ID to identify this authorization request
    request_id = secrets.token_urlsafe(32)
    
    # Store the OAuth request parameters in the database, not in session
    oauth_request = OAuth2Request(
        request_id=request_id,
        callback_url=callback_url,
        scope=scope,
        state=state,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=30)
    )
    db.add(oauth_request)
    db.commit()
    
    # Build the authorization URL with request_id
    authorize_url = f"/oauth/authorize?request_id={request_id}"
    
    # Return the authorization URL to the third-party app
    return {"authorization_url": authorize_url}

@router.get("/oauth/authorize", response_class=HTMLResponse)
async def authorize_page(
    request: Request,
    request_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Render authorization page."""
    # Retrieve the OAuth request from database
    oauth_request = db.query(OAuth2Request).filter(
        OAuth2Request.request_id == request_id,
        OAuth2Request.expires_at > datetime.utcnow()
    ).first()
    
    if not oauth_request:
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired authorization request"
        )
    
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        # If user is not logged in, redirect to login
        # Store request_id in session temporarily so we can redirect back after login
        request.session["pending_oauth_request_id"] = request_id
        login_url = f"/auth/twitter/login?next=/oauth/authorize?request_id={request_id}"
        return RedirectResponse(login_url)
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate a secure token for the authorization form
    form_token = secrets.token_urlsafe(32)
    request.session["oauth_form_token"] = form_token
    
    # Render authorization page
    return templates.TemplateResponse(
        "authorize.html",
        {
            "request": request,
            "user": user,
            "scope": oauth_request.scope,
            "callback_url": oauth_request.callback_url,
            "form_token": form_token,
            "state": oauth_request.state,
            "request_id": request_id
        }
    )
@router.get("/oauth/complete")
async def complete_authorization(
    request: Request,
    request_id: str = Query(...),
    form_token: str = Query(...),
    authorized: bool = Query(...),
    db: Session = Depends(get_db)
):
    """Process authorization decision."""
    # Validate form token
    session_form_token = request.session.get("oauth_form_token")
    if not session_form_token or session_form_token != form_token:
        raise HTTPException(status_code=400, detail="Invalid form submission")
    
    # Check if user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Retrieve the OAuth request from database
    oauth_request = db.query(OAuth2Request).filter(
        OAuth2Request.request_id == request_id,
        OAuth2Request.expires_at > datetime.utcnow()
    ).first()
    
    if not oauth_request:
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired authorization request"
        )
    
    # Get OAuth parameters from the request object
    callback_url = oauth_request.callback_url
    state = oauth_request.state
    scope = oauth_request.scope
    
    if not authorized:
        # User denied authorization
        error_redirect = f"{callback_url}?error=access_denied"
        if state:
            error_redirect += f"&state={state}"
        
        # Clean up
        db.delete(oauth_request)
        db.commit()
        
        # Clear session data
        for key in ["oauth_form_token", "pending_oauth_request_id"]:
            if key in request.session:
                del request.session[key]
                
        return RedirectResponse(error_redirect)
    
    # User authorized, generate token
    token_value = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    token = OAuth2Token(
        token_id=str(uuid.uuid4()),
        access_token=token_value,
        scopes=scope,
        is_active=True,
        expires_at=expires_at,
        user_id=user_id
    )
    db.add(token)
    
    # Mark the OAuth request as used and then delete it
    db.delete(oauth_request)
    db.commit()
    
    # Clean up session data
    for key in ["oauth_form_token", "pending_oauth_request_id"]:
        if key in request.session:
            del request.session[key]
    
    # Redirect to callback with token
    success_redirect = f"{callback_url}?token={token_value}"
    if state:
        success_redirect += f"&state={state}"
    
    return RedirectResponse(success_redirect)

@router.post("/api/oauth1/tweet")
async def oauth1_tweet(
    tweet_data: OAuth1TweetRequest,
    token: OAuth2Token = Security(verify_token_and_scopes, scopes=["twitter_oauth1.tweet"]),
    db: Session = Depends(get_db)
):
    """Post a tweet using OAuth1 credentials"""
    try:
        # Get the user's Twitter account
        twitter_account = db.query(TwitterAccount).filter(
            TwitterAccount.user_id == token.user_id
        ).first()
        
        if not twitter_account:
            logger.error(f"No Twitter account found for user {token.user_id}")
            raise HTTPException(status_code=404, detail="Twitter account not found")
        
        # Get OAuth credentials for this account
        oauth_creds = db.query(TwitterOAuthCredential).filter(
            TwitterOAuthCredential.twitter_account_id == twitter_account.twitter_id
        ).first()
        
        if not oauth_creds:
            logger.error(f"No OAuth credentials found for Twitter account {twitter_account.twitter_id}")
            raise HTTPException(status_code=404, detail="OAuth credentials not found")
        
        # Safety check - can be implemented similar to main.py if needed
        
        # Post tweet using OAuth1
        try:
            tweet_id = twitter_oauth.post_tweet(
                oauth_creds.oauth_token,
                oauth_creds.oauth_token_secret,
                tweet_data.text
            )
            
            # Log successful tweet
            tweet_log = TweetLog(
                user_id=token.user_id,
                tweet_text=tweet_data.text,
                tweet_id=tweet_id,
                safety_check_result=True,
                safety_check_message="OAuth1 tweet"
            )
            db.add(tweet_log)
            db.commit()
            
            return {"status": "success", "tweet_id": tweet_id}
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error posting OAuth1 tweet for user {token.user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") 