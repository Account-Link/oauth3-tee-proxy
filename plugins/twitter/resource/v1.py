# plugins/twitter/resource/v1.py
"""
Twitter v1.1 API Resource Plugin
===============================

This module implements a Twitter v1.1 API resource plugin for the OAuth3 TEE Proxy.
It acts as a passthrough to Twitter's v1.1 REST API, allowing the proxy to
forward requests to Twitter's endpoints without having to maintain
individual functions for each endpoint.

The TwitterV1ResourcePlugin class implements the ResourcePlugin interface,
providing methods for:
- Initializing Twitter v1.1 API clients with user credentials
- Validating v1.1 API clients
- Forwarding API requests to Twitter's v1.1 endpoints
- Supporting all available v1.1 API operations transparently

The plugin uses the TwitterV1Client wrapper class that encapsulates the
interaction with the Twitter v1.1 API.

Supported Scopes:
---------------
- twitter.v1: Permission to make v1.1 API calls
- twitter.v1.read: Permission to make read-only v1.1 API calls
- twitter.v1.write: Permission to make write v1.1 API calls
"""

import logging
import traceback
import json
import httpx
from typing import Dict, Any, Optional, List
import urllib.parse

from plugins.twitter.resource import TwitterBaseResourcePlugin

logger = logging.getLogger(__name__)

class TwitterV1Client:
    """
    Twitter v1.1 API client wrapper used by the resource plugin.
    
    This class provides a passthrough interface to Twitter's v1.1 REST API,
    allowing the TEE Proxy to forward requests without having to maintain
    individual functions for each API operation.
    
    Attributes:
        session (httpx.Client): HTTP client with session cookies for authentication
        base_url (str): Base URL for Twitter's v1.1 API
    """
    
    def __init__(self, cookies: Dict[str, Any]):
        """
        Initialize the v1.1 API client with Twitter cookies.
        
        Args:
            cookies (Dict[str, Any]): The Twitter cookie credentials as a dictionary
        """
        self.session = httpx.Client(cookies=cookies, follow_redirects=True)
        self.base_url = "https://api.twitter.com/1.1"
    
    async def validate(self) -> bool:
        """
        Validate if the client is still working.
        
        Makes a lightweight API call to Twitter to check if the client's
        credentials are still valid.
        
        Returns:
            bool: True if the client is valid, False otherwise
        """
        try:
            # Try a simple API call that should work for authenticated users
            # We use the account/verify_credentials endpoint as it's standard for validation
            response = self.session.get(
                f"{self.base_url}/account/verify_credentials.json"
            )
            # Check if we got a successful response
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error validating Twitter v1.1 client: {e}")
            return False
    
    async def execute_request(
        self, 
        endpoint: str, 
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a request against Twitter's v1.1 API.
        
        This method acts as a passthrough to Twitter's v1.1 API, forwarding
        the request to the appropriate endpoint.
        
        Args:
            endpoint (str): The API endpoint to call (without the base URL)
            method (str): HTTP method to use (GET, POST, PUT, DELETE)
            params (Optional[Dict[str, Any]]): Query parameters for the request
            data (Optional[Dict[str, Any]]): Form data for POST requests
            json_data (Optional[Dict[str, Any]]): JSON data for POST requests
            
        Returns:
            Dict[str, Any]: The API response from Twitter
            
        Raises:
            ValueError: If the request fails or returns an error
            Exception: If any other error occurs during the operation
        """
        try:
            # Ensure endpoint starts with a slash and ends with .json if not already
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
            if not endpoint.endswith('.json'):
                endpoint = endpoint + '.json'
                
            url = f"{self.base_url}{endpoint}"
            
            logger.debug(f"Executing v1.1 API request {method} {endpoint} with params: {params}")
            
            # Execute the request with the appropriate method
            if method.upper() == "GET":
                response = self.session.get(url, params=params)
            elif method.upper() == "POST":
                if json_data:
                    response = self.session.post(url, params=params, json=json_data)
                else:
                    response = self.session.post(url, params=params, data=data)
            elif method.upper() == "PUT":
                if json_data:
                    response = self.session.put(url, params=params, json=json_data)
                else:
                    response = self.session.put(url, params=params, data=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check if the response was successful
            if response.status_code >= 400:
                error_message = f"Twitter v1.1 API request failed with status code {response.status_code}"
                try:
                    error_data = response.json()
                    error_message += f": {json.dumps(error_data)}"
                except:
                    error_message += f": {response.text}"
                raise ValueError(error_message)
            
            # Parse the response JSON
            data = response.json()
            
            return data
        except Exception as e:
            logger.error(f"Error executing v1.1 API request {endpoint}: {e}\nTraceback:\n{traceback.format_exc()}")
            raise

class TwitterV1ResourcePlugin(TwitterBaseResourcePlugin):
    """
    Plugin for Twitter v1.1 API resource operations.
    
    This class implements the ResourcePlugin interface for Twitter v1.1 API operations,
    providing methods for initializing Twitter v1.1 clients, validating clients,
    and executing API requests.
    
    The plugin acts as a passthrough to Twitter's v1.1 API, allowing new API
    operations to be used without requiring code changes to the plugin.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin
        SCOPES (Dict[str, str]): Dictionary mapping scope names to descriptions
    """
    
    service_name = "twitter_v1"
    
    SCOPES = {
        "twitter.v1": "Permission to make v1.1 API calls to Twitter",
        "twitter.v1.read": "Permission to make read-only v1.1 API calls",
        "twitter.v1.write": "Permission to make write v1.1 API calls"
    }
    
    async def initialize_client(self, credentials: Dict[str, Any]) -> TwitterV1Client:
        """
        Initialize Twitter v1.1 client with credentials.
        
        Creates a new TwitterV1Client instance using the provided credentials.
        
        Args:
            credentials (Dict[str, Any]): The Twitter cookie credentials
            
        Returns:
            TwitterV1Client: An initialized Twitter v1.1 client
            
        Raises:
            Exception: If the client cannot be initialized
        """
        try:
            return TwitterV1Client(cookies=credentials)
        except Exception as e:
            logger.error(f"Error initializing Twitter v1.1 client: {e}")
            raise
    
    async def validate_client(self, client: TwitterV1Client) -> bool:
        """
        Validate if the Twitter v1.1 client is still valid.
        
        Checks if the Twitter v1.1 client's credentials are still valid by making
        a lightweight API call to Twitter.
        
        Args:
            client (TwitterV1Client): The client to validate
            
        Returns:
            bool: True if the client is valid, False otherwise
        """
        return await client.validate()
    
    async def execute_v1_request(
        self, 
        client: TwitterV1Client,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a v1.1 API request using the client.
        
        This method acts as a passthrough to the client's execute_request method,
        forwarding the request to Twitter's v1.1 API.
        
        Args:
            client (TwitterV1Client): The Twitter v1.1 client to use
            endpoint (str): The API endpoint to call (without the base URL)
            method (str): HTTP method to use (GET, POST, PUT, DELETE)
            params (Optional[Dict[str, Any]]): Query parameters for the request
            data (Optional[Dict[str, Any]]): Form data for POST requests
            json_data (Optional[Dict[str, Any]]): JSON data for POST requests
            
        Returns:
            Dict[str, Any]: The API response from Twitter
            
        Raises:
            ValueError: If the request fails or returns an error
            Exception: If any other error occurs during the operation
        """
        return await client.execute_request(endpoint, method, params, data, json_data)