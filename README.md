# OAuth3 Twitter Cookie Service

A service for managing Twitter cookies with safety filtering and OAuth2 token support.

AI Agents are used to posting with a Twitter `auth_token` using the undocumented API. This is as powerful as being logged in with the user's twitter account.

This is great when the account owner manages their own agent, but if the agent is managed by an external dev, then an `auth_token` cookie is too much authority to share.

In other words, this breaks down when "hiring in the swarm."

So, we want to have a simple non-custodial Dstack app that gives limited access tokens to a twitter account.

<img src="https://github.com/user-attachments/assets/95f36db6-9577-4c30-9c13-4e586eb65e94" width="70%"/>


## 1. Submit Twitter Cookie
   
<img src="https://github.com/user-attachments/assets/28905327-a5ce-4b53-84d2-6ba4cc0d0cbf" width="50%"/>

## 2. Create OAuth2 Tokens

OAuth2 tokens provide granular control through scopes:
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

# OAuth2 Scopes

The following scopes are available:

- `tweet.post`: Allows posting tweets
- `telegram.post_any`: Allows posting to any connected Telegram channel

OAuth2 tokens:
- Are tied to the account owner's session
- Have a 24-hour expiration by default
- Support multiple scopes per token
- Provide granular access control

### Acknowledgments
Josh @hashwarlock for PRD review and architecture diagram 
Shaw for setting the requirements and user story
