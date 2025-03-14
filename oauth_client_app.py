from fastapi import FastAPI, Request, Depends, Query, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import httpx
import secrets
from starlette.middleware.sessions import SessionMiddleware
import os
from typing import Optional

# Create FastAPI app
app = FastAPI(title="OAuth Client Demo")

# Add session middleware
app.add_middleware(
    SessionMiddleware, 
    secret_key=secrets.token_urlsafe(32)
)

# Configuration
OAUTH_SERVER_URL = "http://localhost:8000"  # Your main server URL
CLIENT_PORT = 5002
CLIENT_URL = f"http://localhost:{CLIENT_PORT}"
CALLBACK_URL = f"{CLIENT_URL}/oauth/callback"

# Home page that shows login button and user status
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Check if user is logged in (has a valid token)
    token = request.session.get("access_token")
    user_info = request.session.get("user_info")
    
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>OAuth Client Demo</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .container {
                    background: #f5f5f5;
                    border-radius: 5px;
                    padding: 20px;
                    margin-top: 20px;
                }
                .button {
                    display: inline-block;
                    background: #1DA1F2;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                }
                .info {
                    margin-top: 20px;
                    padding: 15px;
                    background: #e3f2fd;
                    border-radius: 5px;
                }
                textarea {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    margin-bottom: 10px;
                    font-family: Arial, sans-serif;
                }
                .success {
                    background: #d4edda;
                    color: #155724;
                    padding: 10px;
                    margin-top: 10px;
                    border-radius: 5px;
                }
                .error {
                    background: #f8d7da;
                    color: #721c24;
                    padding: 10px;
                    margin-top: 10px;
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <h1>OAuth Client Demo</h1>
            
            <div class="container">
                <h2>Testing OAuth Flow</h2>
                """ + (
                    f"""
                    <p>You are logged in!</p>
                    <div class="info">
                        <p><strong>Access Token:</strong> {token}</p>
                        <p><strong>User Info:</strong> {user_info}</p>
                    </div>
                    
                    <div class="container">
                        <h3>Create Tweet</h3>
                        <form action="/tweet" method="post">
                            <textarea name="text" rows="4" placeholder="What's happening?" maxlength="280" required></textarea>
                            <button type="submit" class="button">Tweet</button>
                        </form>
                        {request.session.get('tweet_message', '')}
                    </div>
                    
                    <p><a href="/logout" class="button" style="background: #dc3545;">Logout</a></p>
                    """
                    if token else
                    """
                    <p>Click the button below to test the OAuth login flow:</p>
                    <p><a href="/login" class="button">Login with Twitter OAuth</a></p>
                    """
                ) + """
            </div>
            
            <div class="container">
                <h3>How it Works</h3>
                <ol>
                    <li>User clicks "Login with Twitter OAuth"</li>
                    <li>Client app requests authorization URL from the server</li>
                    <li>User is redirected to the authorization page</li>
                    <li>After authorization, server redirects back to client with a token</li>
                    <li>Client app validates and stores the token</li>
                    <li>Once authorized, users can post tweets from the application</li>
                </ol>
            </div>
        </body>
    </html>
    """

# Start OAuth flow
@app.get("/login")
async def login(request: Request):
    # Generate state parameter for security
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    
    # Scopes we want to request - need tweet capability
    scope = "twitter_oauth1.tweet"
    
    # Make request to get authorization URL
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{OAUTH_SERVER_URL}/oauth/get_auth_redirect",
                params={
                    "callback_url": CALLBACK_URL,
                    "scope": scope,
                    "state": state
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to get authorization URL")
            
            # Extract authorization URL from response
            auth_data = response.json()
            auth_url = auth_data.get("authorization_url")
            
            if not auth_url:
                raise HTTPException(status_code=500, detail="Invalid authorization URL")
            
            # Construct full URL
            full_auth_url = f"{OAUTH_SERVER_URL}{auth_url}"
            
            # Redirect user to authorization page
            return RedirectResponse(full_auth_url)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error initiating OAuth flow: {str(e)}")

# OAuth callback endpoint
@app.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    token: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None
):
    # Verify state parameter
    session_state = request.session.get("oauth_state")
    if not session_state or session_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Check for errors
    if error:
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>OAuth Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                    .error {{ background: #ffebee; padding: 15px; border-radius: 5px; }}
                    .button {{ display: inline-block; background: #1DA1F2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                </style>
            </head>
            <body>
                <h1>Authorization Denied</h1>
                <div class="error">
                    <p>You denied the authorization request.</p>
                    <p>Error: {error}</p>
                </div>
                <p><a href="/" class="button">Back to Home</a></p>
            </body>
        </html>
        """)
    
    # Check if token is present
    if not token:
        raise HTTPException(status_code=400, detail="Missing token parameter")
    
    # Store the token in session
    request.session["access_token"] = token
    
    # For demonstration purposes, we'll set some dummy user info
    # In a real app, you would use the token to fetch user data from an API
    request.session["user_info"] = "Authenticated User"
    
    # Clean up state from session
    if "oauth_state" in request.session:
        del request.session["oauth_state"]
    
    # Redirect to home page
    return RedirectResponse("/")

# Logout endpoint
@app.get("/logout")
async def logout(request: Request):
    # Clear session data
    if "access_token" in request.session:
        del request.session["access_token"]
    if "user_info" in request.session:
        del request.session["user_info"]
    
    # Redirect to home page
    return RedirectResponse("/")

# Add tweet endpoint
@app.post("/tweet")
async def create_tweet(request: Request, text: str = Form(...)):
    # Check if user is logged in
    token = request.session.get("access_token")
    if not token:
        return RedirectResponse("/")
    
    # Make API request to post a tweet using OAuth1
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{OAUTH_SERVER_URL}/api/oauth1/tweet",
                headers={"Authorization": f"Bearer {token}"},
                json={"text": text, "bypass_safety": False}
            )
            
            if response.status_code == 200:
                result = response.json()
                request.session["tweet_message"] = f'<div class="success">Tweet posted successfully! Tweet ID: {result.get("tweet_id")}</div>'
            else:
                error_data = response.json()
                request.session["tweet_message"] = f'<div class="error">Failed to post tweet: {error_data.get("detail", "Unknown error")}</div>'
                
        except Exception as e:
            request.session["tweet_message"] = f'<div class="error">Error posting tweet: {str(e)}</div>'
    
    return RedirectResponse("/", status_code=303)

# Start the application
if __name__ == "__main__":
    print(f"Starting OAuth client app on port {CLIENT_PORT}")
    print(f"Open your browser and navigate to {CLIENT_URL}")
    uvicorn.run(app, host="0.0.0.0", port=CLIENT_PORT) 