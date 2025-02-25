# OAuth3 Twitter Cookie Service

A service for managing Twitter cookies and post keys with safety filtering and OAuth2 token support.

AI Agents are used to posting with a Twitter `auth_token` using the undocumented API. This is as powerful as being logged in with the user's twitter account.

This is great when the account owner manages their own agent, but if the agent is managed by an external dev, then an `auth_token` cookie is too much authority to share.

In other words, this breaks down when "hiring in the swarm."

So, we want to have a simple non-custodial Dstack app that gives limited access tokens to a twitter account.

<img src="https://github.com/user-attachments/assets/95f36db6-9577-4c30-9c13-4e586eb65e94" width="70%"/>


## 1. Submit Twitter Cookie
   
<img src="https://github.com/user-attachments/assets/28905327-a5ce-4b53-84d2-6ba4cc0d0cbf" width="50%"/>

## 2. Create Access Tokens

You can either create a Post Key (legacy) or use OAuth2 tokens with scopes for more granular control.

### Post Keys (Legacy)
<img src="https://github.com/user-attachments/assets/b8cc368d-4d67-486c-8e14-85f3e375f9ba" width="50%"/>

### OAuth2 Tokens
OAuth2 tokens provide more granular control through scopes:
- `tweet.post` - Permission to post tweets
- `telegram.post_any` - Permission to post any message to Telegram

## 3. Use the Token to Access APIs

<img src="https://github.com/user-attachments/assets/c4af65cf-1fe9-4015-b57c-6776a43816d1" width="50%"/>

<img src="https://github.com/user-attachments/assets/56d3a416-49ad-4514-acff-f246cea32e7d" width="49%"/>


# Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run development server with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

# API Endpoints

## Web Interface
- `GET /` - Web interface for submitting Twitter cookie
- `GET /dashboard` - Manage post keys and OAuth2 tokens

## API Endpoints

### OAuth2 Endpoints
- `POST /token` - Create new OAuth2 token (requires session authentication)
  - Parameters:
    - `scopes` (form field): Space-separated list of requested scopes (e.g. "tweet.post telegram.post_any")

### Legacy API Endpoints
- `POST /api/cookie` - Submit Twitter cookie
- `POST /api/keys` - Create new post key
- `DELETE /api/keys/{key_id}` - Revoke post key

### Protected Endpoints
- `POST /api/tweet` - Post tweet (supports both OAuth2 and post keys)

# Example Usage

## Submit Twitter Cookie
```bash
curl -X POST http://localhost:8000/api/cookie \
  -H "Content-Type: application/json" \
  -d '{"twitter_cookie": "your_twitter_cookie_string"}'
```

## OAuth2 Token Management

### Create OAuth2 Token
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

### Post Tweet with OAuth2
```bash
curl -X POST http://localhost:8000/api/tweet \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, World!"
  }'
```

## Legacy Post Key Usage

### Create Post Key
```bash
curl -X POST http://localhost:8000/api/keys \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_token" \
  -d '{"name": "My Bot Key"}'
```

### Post Tweet with Post Key
```bash
curl -X POST http://localhost:8000/api/tweet \
  -H "Content-Type: application/json" \
  -d '{
    "post_key": "your_post_key",
    "text": "Hello, World!",
    "bypass_safety": false
  }'
```

### Revoke Post Key
```bash
curl -X DELETE http://localhost:8000/api/keys/your_post_key \
  -H "Cookie: session=your_session_token"
```

# OAuth2 Scopes

The following scopes are available:

- `tweet.post`: Allows posting tweets
- `telegram.post_any`: Allows posting to any connected Telegram channel

OAuth2 tokens:
- Are tied to the account owner's session
- Have a 24-hour expiration by default
- Support multiple scopes per token
- Provide more granular access control than post keys

### Acknowledgments
Josh @hashwarlock for PRD review and architecture diagram 
Shaw for setting the requirements and user story
