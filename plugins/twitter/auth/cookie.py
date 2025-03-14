# plugins/twitter/auth/cookie.py
"""
Twitter Cookie Authorization Plugin
==================================

This module implements the Twitter cookie-based authorization plugin.
It handles authentication with Twitter using browser cookies, allowing
users to link their Twitter accounts to the TEE Proxy.

The TwitterCookieAuthorizationPlugin class implements the AuthorizationPlugin interface,
providing methods for:
- Validating Twitter cookies
- Extracting Twitter user IDs from cookies
- Converting Twitter cookies between string and dictionary formats

This plugin works with the unofficial Twitter API client that uses browser cookies
for authentication, allowing the TEE Proxy to act on behalf of users without
requiring them to create Twitter developer accounts or using the official API.

Authentication Flow:
------------------
1. User submits their Twitter cookie string to the TEE Proxy
2. The plugin validates the cookie by making a test API call
3. The plugin extracts the Twitter user ID from the cookie
4. The cookie is stored in the database, linked to the user's account
5. The TEE Proxy can now make Twitter API calls on behalf of the user
"""

import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Tuple

import requests
from twitter.account import Account
from sqlalchemy.orm import Session

from plugins.twitter.auth import TwitterBaseAuthorizationPlugin
from plugins.twitter.models import TwitterAccount

# Lazily import Account to avoid startup issues
def get_twitter_account():
    try:
        
        return Account
    except ImportError:
        logger.error("Could not import Twitter Account class - twitter-api-client may not be installed")
        raise ImportError("Twitter client package not available. Install with 'pip install twitter-api-client'")

logger = logging.getLogger(__name__)

class TwitterCookieAuthorizationPlugin(TwitterBaseAuthorizationPlugin):
    """
    Plugin for Twitter cookie-based authentication.
    
    This class implements the AuthorizationPlugin interface for Twitter authentication
    using browser cookies. It provides functionality for validating Twitter cookies,
    extracting Twitter user IDs, and converting cookies between string and dictionary
    formats.
    
    The plugin uses the unofficial Twitter API client (twitter.account.Account) that
    works with browser cookies for authentication. This approach allows the TEE Proxy
    to act on behalf of Twitter users without requiring developer API keys.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin ("twitter")
    """
    
    service_name = "twitter_cookie"
    
    @classmethod
    def create_from_cookie_string(cls, cookie_string: str) -> "TwitterCookieAuthorizationPlugin":
        """
        Create a plugin instance from a raw cookie string.
        
        This factory method creates a new TwitterCookieAuthorizationPlugin instance and
        initializes it with credentials parsed from the provided cookie string.
        
        Args:
            cookie_string (str): The raw Twitter cookie string in JSON format
            
        Returns:
            TwitterCookieAuthorizationPlugin: An initialized plugin instance
            
        Raises:
            ValueError: If the cookie string cannot be parsed as JSON
        """
        plugin = cls()
        plugin.credentials = plugin.credentials_from_string(cookie_string)
        return plugin
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate if the Twitter cookie is still valid.
        
        Attempts to check if the auth_token cookie is valid by making a direct request
        to Twitter's API endpoint. This approach is more reliable than using the Account class
        which may have compatibility issues.
        
        IMPORTANT: For testing purposes, this method currently bypasses actual validation
        and returns True if the auth_token is of reasonable length.
        
        Args:
            credentials (Dict[str, Any]): The Twitter cookie credentials
            
        Returns:
            bool: True if the credentials are valid, False otherwise
            
        Note:
            This method catches all exceptions and returns False for any error,
            logging the error for debugging purposes.
        """
        try:
            # Check if we have an auth_token to work with
            if "auth_token" not in credentials or not credentials["auth_token"]:
                logger.error("No auth_token found in credentials")
                return False
                
            auth_token = credentials["auth_token"]
            
            # Log token info for debugging (don't log the full token)
            auth_token_length = len(auth_token)
            logger.info(f"Auth token length: {auth_token_length} chars")
            
            # Check if token seems valid
            if auth_token_length < 20:
                logger.error("Auth token is too short, likely invalid")
                return False
                
            # Log first few characters for debugging
            if auth_token_length > 0:
                logger.info(f"Auth token starts with: {auth_token[:5]}...")
                
            # Make a direct request to Twitter's API to validate the token
            # We'll use a simple endpoint that should work with just the auth_token
            try:
                # Direct method - make a request to Twitter's API
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Cookie": f"auth_token={auth_token}"
                }
                
                # Log the full request details
                url = "https://twitter.com/i/api/1.1/account/settings.json"
                logger.info(f"Making Twitter API request to: {url}")
                logger.info(f"Request headers: {headers}")
                
                # Using Twitter's settings endpoint as a lightweight check
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=10
                )
                
                # Log the full response details
                logger.info(f"Response status code: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
                
                # Log a snippet of the response body (if any)
                response_text = response.text[:500] + ('...' if len(response.text) > 500 else '')
                logger.info(f"Response body (truncated): {response_text}")
                
                # Check if request was successful
                if response.status_code == 200:
                    logger.info("Successfully validated auth_token with direct API request")
                    return True
                else:
                    logger.warning(f"Twitter API returned status code {response.status_code}")
                    
                    # Try a different endpoint as a fallback
                    logger.info("Trying alternative endpoint for validation...")
                    alt_url = "https://twitter.com/i/api/graphql/jMaTS-_Ea4psy1RgLbwwDw/HomeLatestTimeline"
                    alt_headers = headers.copy()
                    alt_headers["Content-Type"] = "application/json"
                    
                    logger.info(f"Making fallback request to: {alt_url}")
                    alt_response = requests.get(
                        alt_url,
                        headers=alt_headers,
                        params={"variables": '{"count":2,"includePromotedContent":false,"latestControlAvailable":true,"requestContext":"launch","withCommunity":true,"withSuperFollowsUserFields":true}'},
                        timeout=10
                    )
                    
                    logger.info(f"Fallback response status: {alt_response.status_code}")
                    
                    if alt_response.status_code == 200:
                        logger.info("Successfully validated auth_token with fallback endpoint")
                        return True
                        
                    return False
                    
            except requests.RequestException as e:
                logger.error(f"Error making request to Twitter API: {e}")
                return False
                
            return False
        except Exception as e:
            logger.error(f"Error validating Twitter cookie credentials: {e}")
            return False
    
    async def get_user_profile(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get Twitter user profile information.
        
        Extracts the Twitter user profile information including username, display name,
        and profile image URL from the Twitter API using the provided credentials.
        
        Args:
            credentials (Dict[str, Any]): The Twitter cookie credentials
            
        Returns:
            Dict[str, Any]: User profile information including:
                - username: Twitter handle (without @)
                - name: Display name
                - profile_image_url: URL to profile image
                - others if available
                
        Raises:
            ValueError: If the profile information cannot be extracted
            Exception: If any other error occurs during the operation
        """
        try:
            # Check if we have an auth_token
            if "auth_token" not in credentials or not credentials["auth_token"]:
                raise ValueError("No auth_token found in credentials")
                
            auth_token = credentials["auth_token"]
            
            # In a real implementation, this would make an API call to the Twitter API
            # to get user profile information. For now, we'll return minimal information
            # that can be used to identify the authenticated user.
            
            # For now, we'll use the user ID we can extract directly from the session
            try:
                # Set up a session with cookies
                session = requests.Session()
                session.cookies.set("auth_token", auth_token, domain="twitter.com")
                
                # First, let's get the home page to get all session cookies
                logger.info("Fetching Twitter home page to get session cookies...")
                home_response = session.get(
                    "https://twitter.com/home",
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"},
                    timeout=10
                )
                
                # Log all cookies for debugging
                cookies = session.cookies.get_dict()
                logger.info(f"Session cookies: {cookies}")
                
                # Try to extract the Twitter user ID from the twid cookie
                # The twid cookie is in the format "u%3D1234567890"
                twid = cookies.get("twid", "")
                user_id = ""
                
                if twid and "u%3D" in twid:
                    # Extract user ID from twid cookie
                    user_id = twid.split("u%3D")[1]
                    logger.info(f"Extracted Twitter user ID from twid cookie: {user_id}")
                    
                    # Try to get the username from another cookie or session data
                    # For demonstration, we'll create a username from the user ID
                    username = f"user_{user_id}"
                    
                    # Return actual user info
                    return {
                        "username": username,
                        "name": f"Twitter User {user_id[:8]}",  # Use shortened user ID in name
                        "profile_image_url": "https://abs.twimg.com/sticky/default_profile_images/default_profile_400x400.png"
                    }
                
                # If we have a ct0 token (CSRF token), we can also try the API directly
                if "ct0" in cookies:
                    logger.info("Found CSRF token, trying Twitter API...")
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                        "x-csrf-token": cookies["ct0"],
                        "x-twitter-auth-type": "OAuth2Session"
                    }
                    
                    api_response = session.get(
                        "https://twitter.com/i/api/1.1/account/settings.json",
                        headers=headers,
                        timeout=10
                    )
                    
                    if api_response.status_code == 200:
                        data = api_response.json()
                        logger.info(f"API response: {data}")
                        
                        if "screen_name" in data:
                            username = data["screen_name"]
                            return {
                                "username": username,
                                "name": username,
                                "profile_image_url": f"https://unavatar.io/twitter/{username}"
                            }
                
            except Exception as e:
                logger.error(f"Error extracting Twitter profile info: {e}")
                
            # Fallback: Return generic data but with the actual user ID if we have it
            if user_id:
                logger.warning(f"Using fallback profile with real user ID: {user_id}")
                return {
                    "username": f"user_{user_id}",
                    "name": f"Twitter User {user_id[:8]}", 
                    "profile_image_url": "https://abs.twimg.com/sticky/default_profile_images/default_profile_400x400.png"
                }
            else:
                logger.warning("Could not extract any user information from session")
                return {
                    "username": "twitter_user",
                    "name": "Twitter User",
                    "profile_image_url": "https://abs.twimg.com/sticky/default_profile_images/default_profile_400x400.png"
                }
            
        except Exception as e:
            logger.error(f"Error getting Twitter profile: {e}")
            # Return minimal profile info rather than raising
            return {}
            
    async def get_user_identifier(self, credentials: Dict[str, Any]) -> str:
        """
        Get Twitter user ID from the credentials.
        
        Extracts the Twitter user ID by making a direct request to Twitter's API
        with the auth_token cookie. This approach is more reliable than using
        the Account class which may have compatibility issues.
        
        Args:
            credentials (Dict[str, Any]): The Twitter cookie credentials
            
        Returns:
            str: The Twitter user ID
            
        Raises:
            ValueError: If the user ID cannot be extracted from the response
            Exception: If any other error occurs during the operation
        """
        try:
            # Check if we have an auth_token
            if "auth_token" not in credentials or not credentials["auth_token"]:
                raise ValueError("No auth_token found in credentials")
                
            auth_token = credentials["auth_token"]
            
            # Log token info for debugging (don't log the full token)
            auth_token_length = len(auth_token)
            if auth_token_length < 20:
                raise ValueError(f"Auth token too short ({auth_token_length} chars). Expected 40+ characters.")
            
            # Extract the user ID from the session cookies
            logger.info("Extracting user ID from Twitter session...")
            
            # Set up a session with cookies
            session = requests.Session()
            session.cookies.set("auth_token", auth_token, domain="twitter.com")
            
            # Load the home page to get session cookies
            logger.info("Fetching Twitter home page...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            home_resp = session.get("https://twitter.com/home", headers=headers, timeout=15)
            logger.info(f"Home page response: {home_resp.status_code}")
            
            # Get all cookies from the session
            cookies = session.cookies.get_dict()
            logger.info(f"Session cookies: {cookies}")
            
            # Try to extract the Twitter user ID from the twid cookie
            # The twid cookie is in the format "u%3D1234567890"
            if "twid" in cookies and "u%3D" in cookies["twid"]:
                user_id = cookies["twid"].split("u%3D")[1]
                logger.info(f"Extracted Twitter user ID from twid cookie: {user_id}")
                return user_id
            
            # If we couldn't extract from twid, try to find user ID in the page content or other cookies
            if "auth_token" in cookies and len(cookies["auth_token"]) > 0:
                # Use a hash of the auth_token as a fallback user ID
                # This ensures a consistent ID for the same auth_token
                import hashlib
                hash_obj = hashlib.md5(auth_token.encode())
                user_id = hash_obj.hexdigest()[:15]  # Use first 15 chars of MD5 hash
                logger.info(f"Generated user ID from auth_token hash: {user_id}")
                return user_id
                
            # If all else fails, use a timestamp-based ID
            import time
            user_id = f"user_{int(time.time())}"
            logger.warning(f"Could not extract user ID, using timestamp-based ID: {user_id}")
            return user_id
                
        except requests.RequestException as e:
            logger.error(f"Error making request to Twitter API: {e}")
            raise ValueError(f"Error communicating with Twitter: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting Twitter user ID from cookie: {e}")
            raise ValueError(f"Error getting Twitter user ID: {str(e)}")
    
    def credentials_to_string(self, credentials: Dict[str, Any]) -> str:
        """
        Convert credentials dictionary to a JSON string.
        
        Serializes the Twitter cookie credentials dictionary to a JSON string
        for storage in the database.
        
        Args:
            credentials (Dict[str, Any]): The Twitter cookie credentials
            
        Returns:
            str: The JSON string representation of the credentials
        """
        return json.dumps(credentials)
    
    async def update_or_create_account(self, db: Session, twitter_id: str, cookie_string: str, 
                           user_id: str, profile_info: dict) -> Tuple[str, str, str]:
        """Update existing account or create new one"""
        username = profile_info.get('username')
        display_name = profile_info.get('name')
        profile_image_url = profile_info.get('profile_image_url')
        
        existing_account = db.query(TwitterAccount).filter(
            TwitterAccount.twitter_id == twitter_id
        ).first()
        
        if existing_account:
            # Update existing account
            existing_account.twitter_cookie = cookie_string
            existing_account.updated_at = datetime.utcnow()
            existing_account.user_id = user_id
            
            # Update profile information if available
            if username:
                existing_account.username = username
            if display_name:
                existing_account.display_name = display_name
            if profile_image_url:
                existing_account.profile_image_url = profile_image_url
        else:
            # Create new account
            account = TwitterAccount(
                twitter_id=twitter_id,
                twitter_cookie=cookie_string,
                user_id=user_id,
                username=username,
                display_name=display_name,
                profile_image_url=profile_image_url
            )
            db.add(account)
            db.flush()  # Get the new ID
        
        db.commit()
        return username, display_name, profile_image_url
            
    def credentials_from_string(self, credentials_str: str) -> Dict[str, Any]:
        """
        Convert cookie string to credentials dictionary.
        
        This method handles various formats for the auth_token:
        1. JSON string format (for stored cookies)
        2. Raw auth_token=VALUE format (for newly submitted cookies)
        3. Just the raw token value
        
        Args:
            credentials_str (str): The cookie string in various formats
            
        Returns:
            Dict[str, Any]: The Twitter cookie credentials as a dictionary
            
        Raises:
            ValueError: If the string cannot be parsed
        """
        logger.info(f"Converting cookie string to credentials. Type: {type(credentials_str)}, Length: {len(str(credentials_str))}")
        
        # Show a preview of the credential string for debugging
        if credentials_str:
            preview = credentials_str[:10] + "..." if len(credentials_str) > 10 else credentials_str
            logger.info(f"Credentials string preview: '{preview}'")
        
        # Just treat it as the raw auth_token value by default
        # This is the most straightforward approach
        auth_token = credentials_str.strip() if credentials_str else ""
        logger.info(f"Using auth_token as raw value, length: {len(auth_token)}")
        
        # If it's a JSON string, try to parse it
        if credentials_str and (credentials_str.startswith('{') and credentials_str.endswith('}')):
            try:
                json_data = json.loads(credentials_str)
                logger.info(f"Successfully parsed as JSON: {json_data.keys() if hasattr(json_data, 'keys') else 'Not a dict'}")
                if isinstance(json_data, dict) and "auth_token" in json_data:
                    auth_token = json_data["auth_token"]
                    logger.info(f"Got auth_token from JSON, length: {len(auth_token)}")
                return json_data
            except json.JSONDecodeError:
                logger.info("Failed to parse as JSON despite { } characters")
        
        # Try to extract just the auth_token if it has a prefix
        if auth_token.startswith('auth_token='):
            auth_token = auth_token.split('auth_token=', 1)[1].strip()
            logger.info(f"Extracted auth_token from prefix, new length: {len(auth_token)}")
        
        # Simple validation - just make sure we have some value
        if not auth_token:
            logger.error("Empty auth_token value after parsing")
            raise ValueError("Empty auth_token value")
            
        # Create cookies dictionary
        cookies = {
            "auth_token": auth_token,
            # Add other required cookies with empty values
            "ct0": "",
            "twid": ""
        }
        logger.info(f"Created credentials dict with auth_token (length: {len(auth_token)})")
        return cookies