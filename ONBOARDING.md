# OAuth3 TEE Proxy — Engineer Onboarding Guide

## 1. Overview and Core Purpose

**What is the OAuth3 TEE Proxy?**  
This application allows users to authenticate with third-party services (e.g., Twitter, Telegram) and proxy requests to those services. It also provides an internal OAuth2 system so that additional clients can request scoped tokens for accessing these integrated services through a single gateway.

Features:

- **Plugin System**: Each external service integration is implemented as a plugin.  
- **Multiple Auth Mechanisms**: The project can authenticate local users via WebAuthn for the proxy dashboard, and authenticate to external services (like Twitter) using either browser cookies or OAuth flows.  
- **Scopes and Policies**: Users or clients can request specific scopes (e.g., `tweet.post`, `telegram.send_message`) to be granted limited permissions.  
- **Database**: Stores user information, credentials, tokens, and logs.  
- **Extensibility**: You can add new integrations by creating new plugins.

---

## 2. Repository Structure

Here’s a high-level look at the directory tree (simplified). The top-level directories you will spend the most time in are **plugins**, **ui_routes**, and the root Python files like **main.py**, **models.py**, etc.

```
/plugins                 # All plugin code (Twitter, Telegram, etc.)
│   ├── twitter          # Twitter-specific plugins
│   │   ├── auth         # Authorization plugin implementations
│   │   ├── resource     # Resource plugin implementations
│   │   ├── routes       # FastAPI routes for Twitter
│   │   └── templates    # Jinja templates unique to Twitter plugin
│   ...
│   └── README.md        # (Out of date - do not rely on this)
│
/ui_routes               # High-level UI routes for the TEE Proxy
│   ├── auth_routes.py   # Standard web login and error handling
│   ├── dashboard_routes.py
│   └── webauthn_routes.py
│
├── main.py              # Application entry point (FastAPI startup)
├── plugin_manager.py    # Core plugin discovery/management
├── oauth2_routes.py     # OAuth2 endpoints for local token issuance
├── models.py            # Core SQLAlchemy models
├── database.py          # DB connection and session management
├── migrations.py        # Alembic-based migrations
├── patches.py           # Applies patches from plugins
├── requirements.txt     # Python dependencies
└── ...
```

Key items:

- **plugins/\_\_init\_\_.py** defines base classes (AuthorizationPlugin, ResourcePlugin, RoutePlugin) and registry functions (e.g., `register_authorization_plugin`).
- **main.py** is where the FastAPI `app` is created and where plugins are discovered.
- **plugin_manager.py** is a higher-level facade for accessing loaded plugins, orchestrating plugin-based routes, etc.
- **ui_routes** folder contains typical endpoints for the user to manage their accounts (dashboard, webauthn, etc.).
- **oauth2_routes.py** handles creation of local OAuth2 tokens (the TEE Proxy’s own token system).
- **migrations.py** plus files in `/migrate_db.py` handle database schema changes.

---

## 3. Main Entry Points

1. **`main.py`**  
   - Creates the FastAPI `app`.  
   - Calls `plugin_manager.discover_plugins()` to load all plugins from `plugins/`.
   - Registers routes from `oauth2_routes`, `ui_routes`, and each plugin’s route plugin.  
   - Applies any patches (e.g., from `plugins/twitter/patches.py`).  

2. **`plugin_manager.py`**  
   - Dynamic discovery of plugin subdirectories (like `plugins/twitter`, `plugins/telegram`).  
   - Contains methods like `get_service_routers()` that each plugin uses to mount its own routes.  
   - Provide factory methods to create plugin instances.

3. **`plugins/__init__.py`** (the plugin system core)  
   - Declares base plugin classes: `AuthorizationPlugin`, `ResourcePlugin`, `RoutePlugin`.  
   - Manages plugin registries: `_authorization_plugins`, `_resource_plugins`, `_route_plugins`.

---

## 4. Configuration and Environment Variables

**Configuration** is handled in two main files:

- **`config.py`**: General application settings (Database URL, session timeouts, secrets, etc.).  
- **`plugins/twitter/config.py`**: Twitter-specific settings (OAuth keys, safety filter, etc.).  
- **`plugins/telegram/config.py`**: Telegram-specific settings (API ID, API hash, etc.).

Settings can be overridden by environment variables. For instance:

- `DATABASE_URL=sqlite:///oauth3.db`
- `TWITTER_CONSUMER_KEY=...`
- `TWITTER_CONSUMER_SECRET=...`

Check `config.py` for the environment variable naming. Check `plugins/twitter/config.py` for Twitter’s environment variable naming (prefixed with `TWITTER_`).

---

## 5. Database and Migrations

The default database is configured in `config.py` via `DATABASE_URL` (SQLite by default).  

- **`database.py`** sets up SQLAlchemy’s engine and session.  
- **`models.py`** defines core models like `User`, `WebAuthnCredential`, `OAuth2Token`, etc.  
- **`plugins/twitter/models.py`** adds Twitter-specific models (e.g., `TwitterAccount`).  
- **`migrations.py`** has a simple Alembic-based approach for schema changes:
  - You can register new migrations in the list `migrations = [...]`.
  - Run `python migrations.py apply` to execute them.

If you add columns or new tables for a plugin, do so via a new migration function and append it to `migrations.py`.

---

## 6. Plugin Architecture

The plugin system is fundamental to how the TEE Proxy integrates with external services. All services (like Twitter, Telegram, etc.) must define:

- **AuthorizationPlugin**:  
  For example, `TwitterCookieAuthorizationPlugin` or `TwitterOAuthAuthorizationPlugin`.  
  These handle the unique details of how to *validate credentials*, *extract user IDs*, and *convert credentials to/from strings*.

- **ResourcePlugin**:  
  For example, `TwitterApiResourcePlugin`.  
  These handle the actual interaction with the external API (posting tweets, calling Telegram, etc.).  

- **RoutePlugin**:  
  E.g., `TwitterRoutes`.  
  These define extra FastAPI routes for that plugin.  

### 6.1 How Plugins Are Registered

When you import a plugin’s `__init__.py`, it calls functions like:

```python
register_authorization_plugin(TwitterCookieAuthorizationPlugin)
register_resource_plugin(TwitterApiResourcePlugin)
register_route_plugin(TwitterRoutes)
...
```

Then, in `main.py`, we run `plugin_manager.discover_plugins()` which:

1. Looks in `plugins/` subdirectories (e.g., `twitter/`, `telegram/`).
2. Imports `plugins.twitter.__init__`.
3. All the plugin classes get registered.

That’s why any new plugin directory must have an `__init__.py` that does the plugin registration.

### 6.2 Authorization Plugins

A class that extends `AuthorizationPlugin`. Must implement methods like:

- `validate_credentials(credentials)`  
- `get_user_identifier(credentials)`  
- `credentials_to_string(credentials)`  
- `credentials_from_string(credentials)`

**Example**: `plugins/twitter/auth/cookie.py` (the `TwitterCookieAuthorizationPlugin`).

### 6.3 Resource Plugins

A class that extends `ResourcePlugin`. Must implement:

- `initialize_client(credentials)`  
- `validate_client(client)`

**Example**: `plugins/twitter/resource/api.py` (the `TwitterApiResourcePlugin`).

### 6.4 Route Plugins

A class that extends `RoutePlugin`. Must implement:

- `get_router()` returning a `FastAPI.APIRouter`.

**Example**: `plugins/twitter/routes/twitter_routes.py` (the `TwitterRoutes` route plugin).

---

## 7. Core Application Flow

1. **User logs in** (to the TEE Proxy) via WebAuthn or existing session.  
2. The user visits the dashboard (served by `ui_routes/dashboard_routes.py`).
3. If the user wants to add or manage a Twitter account:
   - They go to `GET /twitter/auth/admin` (part of `TwitterRoutes` or `TwitterOAuthRoutes`).  
   - They can choose Cookie auth or OAuth-based auth.  
4. **Authorization** plugin is used to validate the provided credentials (cookie or OAuth token).  
5. **Resource** plugin is used to actually interact with the external service once credentials are validated.  

Internally, if an external (third-party) client wants to post tweets, it must obtain an OAuth2 token from `/token` (via `oauth2_routes.py`). That token can have the scope `tweet.post`, which is enforced in the route plugins.

---

## 8. Authentication and WebAuthn

Local authentication for the TEE Proxy is **WebAuthn**-based:

- `/webauthn/register/begin` + `/webauthn/register/complete`  
- `/webauthn/login/begin` + `/webauthn/login/complete`

Implemented in `ui_routes/webauthn_routes.py`.  

- Stores a session token upon successful registration or login.  
- This is how `request.session["user_id"]` is set.

Once logged in, the user can see the main dashboard at `/dashboard`. If they log out or their session is invalid, they must re-auth via WebAuthn.

---

## 9. OAuth2 Token Management

The TEE Proxy can issue its **own** OAuth2 tokens to external apps (e.g., your own web client). The relevant endpoints:

- **POST `/token`** in `oauth2_routes.py`  
  - Expects a user session (i.e., you’re logged into the TEE Proxy’s web UI).  
  - You specify which scopes you want.  
  - The TEE Proxy returns an `access_token` you can use in `Authorization: Bearer` headers.

- **DELETE `/token/{token_id}`**  
  - Revokes a token.

**Scopes** are populated dynamically from the plugins. For instance, the Twitter plugin adds scopes like `tweet.post`, `tweet.read`, `twitter.graphql`, etc.

When you call an endpoint that requires certain scopes, such as `POST /twitter/tweet`, the route will do:

```python
token: OAuth2Token = Security(verify_token_and_scopes, scopes=["tweet.post"])
```

to ensure your token has the `tweet.post` scope.

---

## 10. Twitter Plugin

The Twitter plugin is the most in-depth plugin and a great example of how the system extends to new services.

### 10.1 Cookie-Based Authentication

- **`TwitterCookieAuthorizationPlugin`** (`plugins/twitter/auth/cookie.py`)  
  - Expects the user to submit their Twitter `auth_token` cookie.  
  - Validates it by hitting some Twitter endpoints.  
  - Extracts the user’s Twitter ID from the cookie.  
  - Stores the cookie in the DB `twitter_accounts.twitter_cookie`.

**Routes** for cookie auth are in `plugins/twitter/routes/cookie_routes.py`. For example, `POST /twitter/auth/cookies` is used to submit the cookie.

### 10.2 OAuth1.0a-Based Authentication

- **`TwitterOAuthAuthorizationPlugin`** (`plugins/twitter/auth/oauth.py`)  
  - Uses `tweepy` or direct Twitter OAuth 1.0a flow.  
  - Creates credentials with `oauth_token` and `oauth_token_secret`.  
  - Stored in the `twitter_oauth_credentials` table.

The route plugin class is `TwitterOAuthRoutes` in `plugins/twitter/routes/oauth_routes.py`, which defines `/twitter/oauth/login`, `/twitter/oauth/callback`, etc.

### 10.3 API, GraphQL, and v1.1 Resource Plugins

- **TwitterApiResourcePlugin** (`plugins/twitter/resource/api.py`): The normal (unofficial) Twitter API usage.  
- **TwitterGraphQLResourcePlugin** (`plugins/twitter/resource/graphql.py`): For Twitter’s private GraphQL.  
- **TwitterV1ResourcePlugin** (`plugins/twitter/resource/v1.py`): Passthrough to Twitter’s legacy v1.1 API.

Each is registered in `plugins/twitter/__init__.py`.

### 10.4 Twitter Routes

The Twitter plugin has multiple sets of routes:

1. **`TwitterRoutes`** in `twitter_routes.py` (handles posting tweets, policy checks, etc.).  
2. **`TwitterGraphQLRoutes`** in `graphql_routes.py` (endpoints under `/twitter/graphql`).  
3. **`TwitterV1Routes`** in `v1_routes.py` (endpoints under `/twitter/v1`).  
4. **`TwitterOAuthRoutes`** for OAuth1 flows.  
5. **Cookie-based routes** in `cookie_routes.py`.  

When discovered, these routes are mounted at paths like:

- `/twitter` (the main routes)
- `/twitter/graphql`
- `/twitter/v1`
- `/twitter/oauth`

---

## 11. Telegram Plugin (Optional)

A similar structure exists for Telegram in `plugins/telegram`. It’s optional but follows the same pattern:

- `plugins/telegram/auth.py` (if present, for authentication)
- `plugins/telegram/resource.py`
- `plugins/telegram/routes/...`

If you look at `plugins/telegram/config.py`, you’ll see environment variables like `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`.

---

## 12. Adding a New Plugin

If you want to integrate another service:

1. Create a new directory under `/plugins/my_new_service/`.  
2. Implement at least one `AuthorizationPlugin` subclass in `auth.py` if you need custom authentication.  
3. Implement a `ResourcePlugin` subclass in `resource.py`.  
4. (Optional) Implement a `RoutePlugin` subclass in `routes/...` for endpoints specific to your service.  
5. In your `my_new_service/__init__.py`, import and register your plugins:

   ```python
   from plugins import register_authorization_plugin, register_resource_plugin, register_route_plugin
   from .auth.my_auth import MyServiceAuthorizationPlugin
   from .resource.my_resource import MyServiceResourcePlugin
   from .routes.my_routes import MyServiceRoutes

   register_authorization_plugin(MyServiceAuthorizationPlugin)
   register_resource_plugin(MyServiceResourcePlugin)
   register_route_plugin(MyServiceRoutes)
   ```

6. That’s it. On startup, `plugin_manager.discover_plugins()` will find your new plugin.

---

## 13. Developing Locally

You mentioned that you already have the `.venv` created and the dependencies installed. Typically, the steps are:

1. **Activate the virtual environment** (e.g., `source .venv/bin/activate`).  
2. **Run the server**:

   ```bash
   uv pip run main.py
   ```

   or  

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Visit** `http://localhost:8000` in your browser for the home page.  

**Note**: The user instructions mention an internal tool called `uv pip` that might be used to run Python apps. Alternatively, any normal `uvicorn main:app` approach works. The code references `Dockerfile` and `docker-compose.yml` as well.

---

## 14. Useful Commands

Although you may not need them daily, here are some relevant ones from the code:

- **Run the migrations**:

  ```bash
  python migrations.py apply
  ```

- **Check or add columns to the database** (example migration logic can be found in `migrate_db.py`).
- **Run Tests** (if any test suite is present; you can see `pytest.ini` for config):

  ```bash
  pytest
  ```

- **Manual script**: `check_accounts.py` lets you list Twitter accounts for a user:

  ```bash
  python check_accounts.py
  python check_accounts.py <user_id>
  ```

---

## 15. Troubleshooting and Debugging

1. **Logging**: The code uses Python’s `logging`. By default, it prints to console. Adjust logging level in `main.py` or at runtime with environment variables.  
2. **Patches**: If Twitter features break (like cookie parsing), see `plugins/twitter/patches.py` which monkey-patches the `twitter.account` library.  
3. **Scoping**: If an API request is denied with “missing scope,” check that the token actually has that scope.  
4. **Expired Tokens**: If an OAuth2 token is expired, you’ll get a 401. Check `oauth2_routes.py` for how expiration is enforced.  
5. **Sessions**: Web sessions are stored in cookies (`oauth3_session`) with a configured expiry. Check `SessionMiddleware` usage in `main.py`.

---

## Conclusion

You should now have a clear, code-based understanding of the **OAuth3 TEE Proxy** system, how its plugin architecture works, and how to develop or extend it. Whenever in doubt, **trust the code** over any existing text docs.

Happy coding and welcome aboard! If you need further help:

- **Review**: `main.py`, `plugin_manager.py`, `plugins/__init__.py`
- **Check** the example code in `plugins/twitter/` for a practical blueprint
- **Ask** the team or open issues if something is unclear

Feel free to update or expand this onboarding guide as the code evolves!
