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

Future possibilities:
- Twitter OAuth2 Authorization
- Twitter API Key Authorization

### Resource Servers

Resource servers handle interaction with Twitter APIs and resources. They are responsible for:
- Initializing API clients with user credentials
- Performing operations like posting tweets
- Managing resource-specific permissions (scopes)

Current implementations:
- **TwitterApiResourcePlugin**: Handles Twitter API operations (tweets, etc.)
- **TwitterGraphQLResourcePlugin**: Provides passthrough access to Twitter's private GraphQL API

Future possibilities:
- Twitter Media Resource
- Other specialized Twitter API resources

### Routes

Routes handle HTTP endpoints and user interactions. They are responsible for:
- Providing HTTP endpoints for Twitter functionality
- Handling request/response formatting
- Coordinating between authorization and resource servers

Current implementations:
- **TwitterRoutes**: Provides endpoints for account linking and tweeting
- **TwitterGraphQLRoutes**: Provides endpoints for accessing Twitter's GraphQL API

Future possibilities:
- Dedicated routes for different Twitter features

## GraphQL API

The Twitter plugin now includes support for Twitter's private GraphQL API, allowing direct access to all GraphQL operations that Twitter's web interface uses. This is implemented as a passthrough, meaning the plugin automatically supports new GraphQL operations without requiring code changes.

### Usage

The GraphQL API can be accessed through two endpoints:

#### GET /twitter/graphql/{query_id}

For read operations, used with query parameters:

```
GET /twitter/graphql/PFIxTk8owMoZgiMccP0r4g?variables={"userId":"123456"}&features={"feature1":true}
```

#### POST /twitter/graphql/{query_id}

For write operations, used with JSON body:

```
POST /twitter/graphql/aQKrduk_DA46XfOQDkcEng
Content-Type: application/json

{
  "variables": {
    "userId": "123456"
  },
  "features": {
    "feature1": true
  }
}
```

### Query IDs

The GraphQL API uses query IDs to identify operations. These IDs can be found in the documentation submodule at `docs/twitter-api/docs/markdown/GraphQL.md`.

## Usage

### Adding a Twitter Account

1. User logs in to the OAuth3 TEE Proxy
2. User submits their Twitter cookie to the `/twitter/cookie` endpoint
3. The cookie is validated and stored securely in the TEE Proxy
4. The Twitter account is now linked to the user's profile

### Using Twitter Resources

1. Client requests an OAuth2 token from the TEE Proxy with Twitter scopes
2. Client uses the token to access Twitter resources via the TEE Proxy
3. The TEE Proxy validates the token and scope permissions
4. The TEE Proxy performs the requested operation on behalf of the user

## Supported Operations

- **Posting tweets**: `/twitter/tweet` endpoint with the `tweet.post` scope
- **Reading tweets**: (planned) with the `tweet.read` scope
- **Deleting tweets**: (planned) with the `tweet.delete` scope

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