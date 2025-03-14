# OAuth3 TEE Proxy

A secure proxy service for managing authentication and authorization to various API services with passkey support and JWT-based authentication.

## Overview

The OAuth3 TEE Proxy provides a secure, non-custodial authentication system that enables users to:

1. Register and login using passkeys (WebAuthn)
2. Manage multiple passkeys on a single account
3. Create and manage API tokens with specific permissions
4. View a comprehensive access log for security monitoring
5. Revoke tokens and manage active sessions

## Authentication System

The authentication system uses a combination of passkeys (WebAuthn) and JWT tokens:

### Passkey Authentication

- Users register using passkeys without requiring a username upfront
- Multiple passkeys can be registered to a single account
- Each passkey has detailed metadata (device name, creation date, last used)
- Passkeys can be added, removed, and renamed from the user profile

### JWT Token Authentication

- All authentication uses JWT tokens with a 2-hour expiration
- Tokens contain minimal user data (user_id, policy, token_id)
- Tokens are automatically refreshed when accessed via sessions within 30 minutes of expiry
- All tokens can be viewed and revoked from the user profile
- "Log out other devices" functionality to revoke all tokens except the current one

### Profile Management

- Users can update their profile information after registration
- Optional fields include: username, email, phone number, wallet address
- All profile changes are logged for security

## API Token System

API tokens provide granular control through scopes:
- `tweet.post` - Permission to post tweets
- `telegram.post_any` - Permission to post any message to Telegram
- (Additional scopes provided by plugins)

## Security Features

- All authentication events are logged and visible to users
- Comprehensive access logging for security monitoring
- Tokens can be individually revoked or all revoked at once
- Each token has a unique ID stored in the database for tracking
- Sessions automatically refresh tokens before expiry

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run development server with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

3. Visit http://localhost:8000 to access the application

## Plugin System

The OAuth3 TEE Proxy uses a plugin system for integrating with different services:

- Each service (Twitter, Telegram, etc.) is implemented as a plugin
- Plugins define their own scopes, routes, and authentication requirements
- New services can be added by creating new plugins without modifying the core code

## Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the development server: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
4. Run tests: `pytest`

## License

[MIT License](LICENSE)