# Twitter Plugin for OAuth3 TEE Proxy

This plugin provides Twitter integration for the OAuth3 TEE Proxy, allowing users to authenticate with Twitter and perform Twitter operations through the TEE Proxy.

## Architecture

The Twitter plugin follows the OAuth3 separation of concerns between Authorization Servers and Resource Servers:

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

Future possibilities:
- Twitter GraphQL API Resource
- Twitter Media Resource

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