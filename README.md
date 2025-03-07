# OAuth3 Service

A flexible OAuth3 service for secure delegation of access to social media accounts and other APIs.

## Overview

OAuth3 provides a secure way to grant limited access to your accounts without sharing full credentials. The service supports multiple authentication methods and delegation patterns.

<img src="https://github.com/user-attachments/assets/95f36db6-9577-4c30-9c13-4e586eb65e94" width="70%"/>

## Key Use Cases

### 1. User-Initiated Delegation

Users can generate limited-scope tokens directly from the dashboard to delegate specific permissions to other applications or agents.

**Example: Twitter Cookie Delegation**  
AI Agents often post tweets using a Twitter `auth_token` cookie. This has the same power as being logged into the user's Twitter account. OAuth3 allows users to create limited-scope tokens for safer delegation.

<img src="https://github.com/user-attachments/assets/28905327-a5ce-4b53-84d2-6ba4cc0d0cbf" width="50%"/>
<img src="https://github.com/user-attachments/assets/c4af65cf-1fe9-4015-b57c-6776a43816d1" width="50%"/>
<img src="https://github.com/user-attachments/assets/56d3a416-49ad-4514-acff-f246cea32e7d" width="49%"/>


### 2. Client-Initiated Delegation (Three-Legged OAuth)

Applications can initiate an OAuth flow to request specific permissions from users.

1. Client application redirects user to OAuth3
2. User authenticates and authorizes specific permissions
3. User is redirected back to client application with access token

This is exactly the standard OAuth2 flow, just to a TEE-based proxy.


## Authentication Methods

The service supports multiple authentication methods:

1. **Twitter OAuth1 Authentication**
   - Create accounts using Twitter credentials
   - Link Twitter accounts to existing accounts
   - Authorize applications to post tweets on your behalf

2. **Twitter Cookie Authentication**
   - Submit your Twitter cookie for API access with fine-grained permissions

3. **WebAuthn/Passkey Authentication**
   - Use passkeys for secure passwordless authentication

## Available Scopes

OAuth3 tokens provide granular control through scopes:
- `tweet.post`: Allows posting tweets via cookie-based authentication
- `telegram.post_any`: Allows posting to any connected Telegram channel
- `twitter_oauth1.auth`: Allows requesting auth URLs for Twitter OAuth1
- `twitter_oauth1.tweet`: Allows posting tweets via Twitter OAuth1 credentials

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
# Twitter OAuth credentials
export TWITTER_CONSUMER_KEY="your_consumer_key"
export TWITTER_CONSUMER_SECRET="your_consumer_secret"
export TWITTER_OAUTH_CALLBACK_URL="http://localhost:8000/auth/twitter/callback"
```

3. Run development server with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. Run the sample OAuth3 client app (optional):
```bash
python oauth_client_app.py
```
This will start a demo client on port 5002 that demonstrates the OAuth flow.

## API Endpoints

### Web Interface
- `GET /` - Web interface for authentication and token management
- `GET /dashboard` - Manage OAuth3 tokens and connected accounts

### OAuth2 Endpoints
- `POST /token` - Create new OAuth3 token (requires session authentication)
  - Parameters:
    - `scopes` (form field): Space-separated list of requested scopes (e.g. "tweet.post telegram.post_any")

### Twitter OAuth1 Endpoints
- `GET /auth/twitter/login` - Initiate Twitter OAuth1 login flow
- `GET /auth/twitter/callback` - Handle Twitter OAuth1 callback
- `GET /oauth/get_auth_redirect` - Generate authorization URL for third-party apps
- `GET /oauth/authorize` - Authorization page for third-party apps
- `POST /api/oauth1/tweet` - Post a tweet using OAuth1 credentials (requires OAuth3 token)

### Twitter Cookie Management
- `POST /api/cookie` - Submit Twitter cookie

### Protected Endpoints
- `POST /api/tweet` - Post tweet (requires OAuth3 token)

## Example Usage

### Submit Twitter Cookie
```bash
curl -X POST http://localhost:8000/api/cookie \
  -H "Content-Type: application/json" \
  -d '{"twitter_cookie": "your_twitter_cookie_string"}'
```

### Create OAuth3 Token
```bash
curl -X POST http://localhost:8000/token \
  -H "Cookie: oauth3_session=your_session_cookie" \
  -d "scopes=tweet.post"
```

Response:
```json
{
  "access_token": "your_access_token",
  "token_type": "bearer",
  "scope": "tweet.post",
  "expires_in": 86400
}
```

### Post Tweet with OAuth3 Token
```bash
curl -X POST http://localhost:8000/api/tweet \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, World!"
  }'
```

### Get Authorization URL for Third-Party App
```bash
curl -X GET "http://localhost:8000/oauth/get_auth_redirect?callback_url=http://myapp.com/callback&scope=twitter_oauth1.tweet&state=1234567890"
```

Response:
```json
{
  "authorization_url": "/oauth/authorize?request_id=abcdefghijklmnopqrstuvwxyz"
}
```

### Post Tweet with OAuth1 Credentials
```bash
curl -X POST http://localhost:8000/api/oauth1/tweet \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from OAuth1!",
    "bypass_safety": false
  }'
```

## Sample OAuth3 Client App

The project includes a sample OAuth3 client application that demonstrates the complete OAuth flow:

1. User clicks "Login with Twitter OAuth" in the client app
2. Client app requests an authorization URL from the server
3. User is redirected to the authorization page (possibly through Twitter login first)
4. After authorization, the server redirects back to the client with a token
5. Client app uses the token to post tweets via the server's API

To test this flow:
1. Start the main server: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
2. In another terminal, start the client app: `python oauth_client_app.py`
3. Open your browser to `http://localhost:5002`
4. Follow the instructions to test the OAuth flow

## OAuth3 Token Properties

- Are tied to the account owner's session
- Have a 24-hour expiration by default
- Support multiple scopes per token
- Provide granular access control

### Acknowledgments
Josh @hashwarlock for PRD review and architecture diagram 
Shaw for setting the requirements and user story
LSDan for investigating oauth1 and oauth2
