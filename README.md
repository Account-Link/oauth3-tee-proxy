# OAuth3 Twitter Cookie Service

A service for managing Twitter cookies and post keys with safety filtering.

AI Agents are used to posting with a Twitter `auth_token` using the undocumented API. This is as powerful as being logged in with the user’s twitter account.

This is great when the account owner manages their own agent, but if the agent is managed by an external dev, then an `auth_token` cookie is too much authority to share.

In other words, this breaks down when "hiring in the swarm."

So, we want to have a simple non-custodial Dstack app that gives limited access tokens to a twitter account.

## 1. Submit Twitter Cookie
   
<img src="https://github.com/user-attachments/assets/28905327-a5ce-4b53-84d2-6ba4cc0d0cbf" width="50%"/>

## 2. Create a "Post Keys"

<img src="https://github.com/user-attachments/assets/b8cc368d-4d67-486c-8e14-85f3e375f9ba" width="50%"/>

## 3. Use the "Post Key" to tweet

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
- `GET /dashboard` - Manage post keys

## API Endpoints
- `POST /api/cookie` - Submit Twitter cookie
- `POST /api/keys` - Create new post key
- `DELETE /api/keys/{key_id}` - Revoke post key
- `POST /api/tweet` - Post tweet using post key

# Example Usage

## Submit Twitter Cookie
```bash
curl -X POST http://localhost:8000/api/cookie \
  -H "Content-Type: application/json" \
  -d '{"twitter_cookie": "your_twitter_cookie_string"}'
```

## Create Post Key
```bash
curl -X POST http://localhost:8000/api/keys \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_token" \
  -d '{"name": "My Bot Key"}'
```

## Post Tweet
```bash
curl -X POST http://localhost:8000/api/tweet \
  -H "Content-Type: application/json" \
  -d '{
    "post_key": "your_post_key",
    "text": "Hello, World!",
    "bypass_safety": false
  }'
```

## Revoke Post Key
```bash
curl -X DELETE http://localhost:8000/api/keys/your_post_key \
  -H "Cookie: session=your_session_token"
``` 
