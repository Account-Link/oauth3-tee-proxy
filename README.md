# OAuth3 Twitter Cookie Service

A service for managing Twitter cookies and post keys with safety filtering.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run development server with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Web Interface
- `GET /` - Web interface for submitting Twitter cookie
- `GET /dashboard` - Manage post keys

### API Endpoints
- `POST /api/cookie` - Submit Twitter cookie
- `POST /api/keys` - Create new post key
- `DELETE /api/keys/{key_id}` - Revoke post key
- `POST /api/tweet` - Post tweet using post key

## Example Usage

### Submit Twitter Cookie
```bash
curl -X POST http://localhost:8000/api/cookie \
  -H "Content-Type: application/json" \
  -d '{"twitter_cookie": "your_twitter_cookie_string"}'
```

### Create Post Key
```bash
curl -X POST http://localhost:8000/api/keys \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_token" \
  -d '{"name": "My Bot Key"}'
```

### Post Tweet
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