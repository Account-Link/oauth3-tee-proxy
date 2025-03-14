# Twitter Plugin for OAuth3 TEE Proxy

This plugin provides Twitter integration for the OAuth3 TEE Proxy, allowing users to authenticate with Twitter and perform Twitter operations through the TEE Proxy.

## Architecture

The Twitter plugin follows the OAuth3 separation of concerns with three distinct components:

### Authorization Servers

Authorization servers handle user authentication with Twitter and credential management. They are responsible for:
- Validating Twitter credentials
- Extracting user identifiers
- Managing secure storage of credentials

Current implementations:
- **TwitterCookieAuthorizationPlugin**: Handles authentication using browser cookies
- **TwitterOAuthAuthorizationPlugin**: Handles authentication using Twitter's OAuth 1.0a flow

### Resource Servers

Resource servers handle interaction with Twitter APIs and resources. They are responsible for:
- Initializing API clients with user credentials
- Performing operations like posting tweets
- Managing resource-specific permissions (scopes)

Current implementations:
- **TwitterApiResourcePlugin**: Handles Twitter API operations (tweets, etc.)
- **TwitterGraphQLResourcePlugin**: Provides passthrough access to Twitter's private GraphQL API
- **TwitterV1ResourcePlugin**: Provides passthrough access to Twitter's v1.1 REST API

Future possibilities:
- Twitter Media Resource
- Other specialized Twitter API resources

### Routes

Routes handle HTTP endpoints and user interactions. They are responsible for:
- Providing HTTP endpoints for Twitter functionality
- Handling request/response formatting
- Coordinating between authorization and resource servers

Current implementations:
- **TwitterRoutes**: Main Twitter functionality routes
- **TwitterOAuthRoutes**: Twitter OAuth authentication routes
- **TwitterGraphQLRoutes**: Twitter GraphQL API routes
- **TwitterV1Routes**: Twitter v1.1 REST API routes

## UI Components

The Twitter plugin provides the following UI components for user interaction:

| Component | URL | Description |
|-----------|-----|-------------|
| Authentication Admin | `/twitter/auth/admin` | Authentication management with both cookie and OAuth options |
| Dashboard Widget | N/A | Twitter accounts management widget on the dashboard |
| GraphQL Playground | `/twitter/graphql/playground` | Interactive GraphQL explorer |

## API Reference

### Authentication API

#### Cookie Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/twitter/auth/cookies` | Submits and validates Twitter cookie |

#### OAuth Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/twitter/oauth/login` | Initiates Twitter OAuth login flow |
| GET | `/twitter/oauth/link` | Links Twitter account to existing user |
| GET | `/twitter/oauth/callback` | Handles callback from Twitter OAuth |

### Account Management API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/twitter/accounts` | Lists linked Twitter accounts |
| DELETE | `/twitter/accounts/{twitter_id}` | Deletes a linked Twitter account |
| DELETE | `/twitter/accounts` | Deletes all linked Twitter accounts |

### Tweet Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/twitter/tweet` | Posts a tweet |

### Policy Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/twitter/policy` | Gets current Twitter operations policy |
| PUT | `/twitter/policy` | Updates Twitter operations policy |
| GET | `/twitter/policy/operations` | Lists available policy operations |
| GET | `/twitter/policy/templates/{template_name}` | Gets a predefined policy template |

### GraphQL API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/twitter/graphql/{query_id}` | Executes read GraphQL operation |
| POST | `/twitter/graphql/{query_id}` | Executes write GraphQL operation |

### v1.1 REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/twitter/v1/{endpoint}` | Executes v1.1 API GET request |
| POST | `/twitter/v1/{endpoint}` | Executes v1.1 API POST request |
| PUT | `/twitter/v1/{endpoint}` | Executes v1.1 API PUT request |
| DELETE | `/twitter/v1/{endpoint}` | Executes v1.1 API DELETE request |

## UI Components Details

### Twitter Authentication Management (`/twitter/auth/admin`)

The Twitter authentication management page provides a complete interface for:
- Adding Twitter accounts via cookie authentication
- Adding Twitter accounts via OAuth authentication
- Viewing authentication methods for each account

The page features a tabbed interface with two authentication options:

1. **Cookie Authentication**: Allows users to submit Twitter cookies by following step-by-step instructions
2. **OAuth Authentication**: Provides a simple "Connect with Twitter" button that initiates the OAuth flow

Users can have both authentication methods for the same Twitter account, providing redundancy and flexibility. The Twitter accounts on the dashboard will show which authentication methods are active for each account.

### Twitter GraphQL Playground (`/twitter/graphql/playground`)

The GraphQL Playground provides an interactive interface for:
- Exploring available GraphQL queries
- Testing GraphQL queries with your Twitter credentials
- Viewing documentation for Twitter's GraphQL API

## API Details

### Cookie Authentication API

#### POST `/twitter/auth/cookies`

Submits and validates a Twitter authentication cookie.

- **Authentication**: Required
- **Request Format**:
  - Form data: `twitter_cookie=auth_token=xyz; ct0=123`
  - OR JSON: `{"cookie": "auth_token=xyz; ct0=123"}`
- **Response**:
  - Success (201): Twitter account successfully linked
    ```json
    {
      "status": "success",
      "message": "Twitter account successfully linked",
      "account": {
        "twitter_id": "123456789",
        "username": "twitteruser",
        "display_name": "Twitter User",
        "profile_image_url": "https://pbs.twimg.com/profile_images/..."
      }
    }
    ```
  - Error (400/401/500): Error message
    ```json
    {
      "detail": "Error message"
    }
    ```

### OAuth Authentication

#### GET `/twitter/oauth/login`

Initiates the Twitter OAuth login flow for user authentication.

- **Authentication**: Not required
- **Query Parameters**:
  - `next` (optional): URL to redirect to after successful authentication
  - `callback_url` (optional): Custom callback URL for the OAuth flow
- **Response**: Redirects to Twitter for authentication

#### GET `/twitter/oauth/link`

Links a Twitter account to an existing authenticated user using OAuth.

- **Authentication**: Required
- **Query Parameters**:
  - `next` (optional): URL to redirect to after successful linking
  - `callback_url` (optional): Custom callback URL for the OAuth flow
- **Response**: Redirects to Twitter for authentication

#### GET `/twitter/oauth/callback`

Handles the callback from Twitter after user authorization.

- **Authentication**: Not required
- **Query Parameters**:
  - `oauth_token`: The OAuth token returned by Twitter
  - `oauth_verifier`: The OAuth verifier returned by Twitter
- **Response**: Redirects to success or error page

### Account Management

#### GET `/twitter/accounts`

Lists all Twitter accounts linked to the authenticated user.

- **Authentication**: Required
- **Response**: List of linked Twitter accounts
  ```json
  {
    "accounts": [
      {
        "twitter_id": "123456789",
        "username": "twitteruser",
        "display_name": "Twitter User",
        "profile_image_url": "https://pbs.twimg.com/profile_images/...",
        "can_login": true,
        "created_at": "2023-01-01T00:00:00Z"
      }
    ]
  }
  ```

#### DELETE `/twitter/accounts/{twitter_id}`

Deletes a specific Twitter account linked to the authenticated user.

- **Authentication**: Required
- **Path Parameters**:
  - `twitter_id`: The Twitter ID of the account to delete
- **Response**:
  - Success (200): Account deleted
    ```json
    {
      "status": "success",
      "message": "Twitter account deleted"
    }
    ```
  - Error (404/403): Error message

#### DELETE `/twitter/accounts`

Deletes all Twitter accounts linked to the authenticated user.

- **Authentication**: Required
- **Response**:
  - Success (200): All accounts deleted
    ```json
    {
      "status": "success",
      "message": "All Twitter accounts deleted",
      "count": 2
    }
    ```

### Tweet Operations

#### POST `/twitter/tweet`

Posts a tweet using the authenticated user's Twitter account.

- **Authentication**: Required (with `tweet.post` scope)
- **Request Body**:
  ```json
  {
    "text": "Hello world from OAuth3 TEE Proxy!",
    "reply_to_tweet_id": "1234567890", // Optional
    "quote_tweet_id": "0987654321" // Optional
  }
  ```
- **Response**:
  - Success (200): Tweet posted
    ```json
    {
      "tweet_id": "1234567890",
      "text": "Hello world from OAuth3 TEE Proxy!"
    }
    ```
  - Error (400/403/500): Error message

### Policy Management

#### GET `/twitter/policy`

Gets the current Twitter operations policy for the authenticated user.

- **Authentication**: Required (with `twitter.policy.read` scope)
- **Response**: Current policy settings
  ```json
  {
    "allowed_operations": ["tweet"],
    "allowed_categories": ["read", "write"]
  }
  ```

#### PUT `/twitter/policy`

Updates the Twitter operations policy for the authenticated user.

- **Authentication**: Required (with `twitter.policy.write` scope)
- **Request Body**:
  ```json
  {
    "allowed_operations": ["tweet"],
    "allowed_categories": ["read"]
  }
  ```
- **Response**:
  - Success (200): Policy updated
    ```json
    {
      "status": "success",
      "message": "Policy updated"
    }
    ```
  - Error (400/500): Error message

#### GET `/twitter/policy/operations`

Gets all available Twitter operations that can be configured in the policy.

- **Authentication**: Required (with `twitter.policy.read` scope)
- **Response**: Available operations
  ```json
  {
    "tweet": "Post a tweet"
  }
  ```

#### GET `/twitter/policy/templates/{template_name}`

Gets a predefined policy template.

- **Authentication**: Required (with `twitter.policy.read` scope)
- **Path Parameters**:
  - `template_name`: Template name (`default`, `read_only`, or `write_only`)
- **Response**: Template policy settings
  ```json
  {
    "allowed_operations": ["tweet"],
    "allowed_categories": ["read", "write"]
  }
  ```

### GraphQL API

#### GET `/twitter/graphql/{query_id}`

Executes a read GraphQL operation with the given query ID.

- **Authentication**: Required (with `twitter.graphql.read` scope)
- **Path Parameters**:
  - `query_id`: The Twitter GraphQL query ID
- **Query Parameters**:
  - `variables` (optional): JSON string of variables
  - `features` (optional): JSON string of feature flags
- **Response**: GraphQL operation result

#### POST `/twitter/graphql/{query_id}`

Executes a write GraphQL operation with the given query ID.

- **Authentication**: Required (with `twitter.graphql.write` scope)
- **Path Parameters**:
  - `query_id`: The Twitter GraphQL query ID
- **Request Body**:
  ```json
  {
    "variables": {
      "key": "value"
    },
    "features": {
      "feature1": true
    }
  }
  ```
- **Response**: GraphQL operation result

### v1.1 REST API

#### GET `/twitter/v1/{endpoint}`

Executes a v1.1 API GET request.

- **Authentication**: Required (with `twitter.v1.read` scope)
- **Path Parameters**:
  - `endpoint`: The v1.1 API endpoint (e.g., `statuses/home_timeline.json`)
- **Query Parameters**:
  - `params` (optional): JSON string of additional parameters
- **Response**: v1.1 API response

#### POST `/twitter/v1/{endpoint}`

Executes a v1.1 API POST request.

- **Authentication**: Required (with `twitter.v1.write` scope)
- **Path Parameters**:
  - `endpoint`: The v1.1 API endpoint (e.g., `statuses/update.json`)
- **Query Parameters**:
  - `is_json` (optional): Whether the body is JSON (default: true)
- **Request Body**: JSON data or form data
- **Response**: v1.1 API response

#### PUT `/twitter/v1/{endpoint}`

Executes a v1.1 API PUT request.

- **Authentication**: Required (with `twitter.v1.write` scope)
- **Path Parameters**:
  - `endpoint`: The v1.1 API endpoint
- **Request Body**: JSON data
- **Response**: v1.1 API response

#### DELETE `/twitter/v1/{endpoint}`

Executes a v1.1 API DELETE request.

- **Authentication**: Required (with `twitter.v1.write` scope)
- **Path Parameters**:
  - `endpoint`: The v1.1 API endpoint (e.g., `statuses/destroy/1234567890.json`)
- **Response**: v1.1 API response

## Scopes

The following OAuth2 scopes are available for Twitter operations:

| Scope | Description |
|-------|-------------|
| `tweet.post` | Permission to post tweets |
| `twitter.v1` | General permission for all v1.1 API calls |
| `twitter.v1.read` | Permission for read-only v1.1 API calls (GET) |
| `twitter.v1.write` | Permission for write v1.1 API calls (POST, PUT, DELETE) |
| `twitter.graphql` | General permission for all GraphQL API calls |
| `twitter.graphql.read` | Permission for read-only GraphQL API calls |
| `twitter.graphql.write` | Permission for write GraphQL API calls |
| `twitter.policy.read` | Permission to read Twitter policy settings |
| `twitter.policy.write` | Permission to update Twitter policy settings |
| `twitter_oauth1.auth` | Permission to authenticate using Twitter OAuth |
| `twitter_oauth1.tweet` | Permission to post tweets using Twitter OAuth |

## Configuration

Edit `.env` file to add necessary settings:

```bash
# Twitter API settings
TWITTER_CONSUMER_KEY=your_consumer_key
TWITTER_CONSUMER_SECRET=your_consumer_secret
TWITTER_OAUTH_CALLBACK_URL=http://localhost:8000/twitter/oauth/callback
```

### Twitter OAuth Setup Guide

To enable Twitter OAuth authentication:

1. Create a Twitter Developer Account:
   - Go to [Twitter Developer Portal](https://developer.twitter.com/)
   - Sign up for a developer account if you don't have one

2. Create a Twitter App:
   - In the Developer Portal, go to "Projects & Apps" > "Create App"
   - Name your app something like "OAuth3 TEE Proxy"
   - Select the appropriate app type and use case

3. Configure OAuth Settings:
   - In your app settings, go to "Settings" > "Authentication settings"
   - Enable "OAuth 1.0a"
   - Set the callback URL to: `http://localhost:8000/twitter/oauth/callback`
   - Request email address access if needed
   - Save your settings

4. Copy API Keys:
   - From the "Keys and tokens" tab, copy the:
     - API Key (Consumer Key)
     - API Key Secret (Consumer Secret)

5. Add to `.env` File:
   ```bash
   TWITTER_CONSUMER_KEY=your_consumer_key
   TWITTER_CONSUMER_SECRET=your_consumer_secret
   TWITTER_OAUTH_CALLBACK_URL=http://localhost:8000/twitter/oauth/callback
   ```

6. Restart the Server:
   - Restart the OAuth3 TEE Proxy server to load the new settings

7. Test the OAuth Flow:
   - Go to `/twitter/auth/admin`
   - Click on the "OAuth Authentication" tab
   - Click "Connect with Twitter"
   - You should be redirected to Twitter to authorize your app

**Note**: Twitter OAuth 1.0a tokens don't expire, so once a user authorizes your app, they won't need to re-authorize unless they explicitly revoke access.

## Database Migrations

The Twitter plugin requires database migrations to set up the necessary tables and columns. Run the following command to apply the migrations:

```bash
python migrations.py apply
```

This will:
1. Add the `policy_json` column to the `twitter_accounts` table
2. Add the `can_login` column to the `twitter_accounts` table
3. Create the `twitter_oauth_credentials` table for storing OAuth tokens

## Extending the Plugin

To add new Twitter authorization methods or resource capabilities:

### Adding a New Authorization Server

1. Create a new file in the `auth/` directory
2. Implement a new class that extends `TwitterBaseAuthorizationPlugin`
3. Register the plugin in `__init__.py`

### Adding a New Resource Server

1. Create a new file in the `resource/` directory
2. Implement a new class that extends `TwitterBaseResourcePlugin`
3. Register the plugin in `__init__.py`