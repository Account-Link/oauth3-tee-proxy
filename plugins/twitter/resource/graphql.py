# plugins/twitter/resource/graphql.py
"""
Twitter GraphQL API Resource Plugin
=================================

This module implements a Twitter GraphQL API resource plugin for the OAuth3 TEE Proxy.
It acts as a passthrough to Twitter's private GraphQL API, allowing the proxy to
forward requests to Twitter's GraphQL endpoints without having to maintain
individual functions for each endpoint.

The TwitterGraphQLResourcePlugin class implements the ResourcePlugin interface,
providing methods for:
- Initializing Twitter GraphQL API clients with user credentials
- Validating GraphQL API clients
- Forwarding GraphQL queries to Twitter's API
- Supporting all available GraphQL operations transparently

The plugin uses the TwitterGraphQLClient wrapper class that encapsulates the
interaction with the Twitter GraphQL API.

Supported Scopes:
---------------
- twitter.graphql: Permission to make GraphQL API calls
"""

import logging
import traceback
import json
import httpx
from typing import Dict, Any, List, Optional

from plugins.twitter.resource import TwitterBaseResourcePlugin

logger = logging.getLogger(__name__)

class TwitterGraphQLClient:
    """
    Twitter GraphQL client wrapper used by the resource plugin.
    
    This class provides a passthrough interface to Twitter's private GraphQL API,
    allowing the TEE Proxy to forward requests without having to maintain
    individual functions for each GraphQL operation.
    
    Attributes:
        session (httpx.Client): HTTP client with session cookies for authentication
        base_url (str): Base URL for Twitter's GraphQL API
    """
    
    def __init__(self, cookies: Dict[str, Any]):
        """
        Initialize the GraphQL client with Twitter cookies.
        
        Args:
            cookies (Dict[str, Any]): The Twitter cookie credentials as a dictionary
        """
        self.session = httpx.Client(cookies=cookies, follow_redirects=True)
        self.base_url = "https://twitter.com/i/api/graphql"
    
    async def validate(self) -> bool:
        """
        Validate if the client is still working.
        
        Makes a lightweight GraphQL API call to Twitter to check if the client's
        credentials are still valid.
        
        Returns:
            bool: True if the client is valid, False otherwise
        """
        try:
            # Try a simple GraphQL query that should work for authenticated users
            # We use the getAltTextPromptPreference query as it's lightweight
            response = self.session.get(
                f"{self.base_url}/PFIxTk8owMoZgiMccP0r4g/getAltTextPromptPreference"
            )
            # Check if we got a successful response
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error validating Twitter GraphQL client: {e}")
            return False
    
    async def execute_query(
        self, 
        query_id: str, 
        variables: Optional[Dict[str, Any]] = None,
        features: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query against Twitter's API.
        
        This method acts as a passthrough to Twitter's GraphQL API, forwarding
        the query ID, variables, and features to the appropriate endpoint.
        
        Args:
            query_id (str): The GraphQL query ID to execute
            variables (Optional[Dict[str, Any]]): Variables to pass to the query
            features (Optional[Dict[str, Any]]): Feature flags to pass to the query
            method (str): HTTP method to use (GET or POST)
            
        Returns:
            Dict[str, Any]: The GraphQL response from Twitter
            
        Raises:
            ValueError: If the query fails or returns an error
            Exception: If any other error occurs during the operation
        """
        try:
            url = f"{self.base_url}/{query_id}"
            params = {}
            
            if variables:
                params["variables"] = json.dumps(variables)
            if features:
                params["features"] = json.dumps(features)
            
            logger.debug(f"Executing GraphQL query {query_id} with params: {params}")
            
            if method.upper() == "POST":
                response = self.session.post(url, json=params)
            else:
                response = self.session.get(url, params=params)
            
            # Check if the response was successful
            if response.status_code != 200:
                error_message = f"GraphQL query failed with status code {response.status_code}"
                try:
                    error_data = response.json()
                    error_message += f": {json.dumps(error_data)}"
                except:
                    error_message += f": {response.text}"
                raise ValueError(error_message)
            
            # Parse the response JSON
            data = response.json()
            
            # Check for GraphQL errors
            if "errors" in data and data["errors"]:
                raise ValueError(f"GraphQL query returned errors: {json.dumps(data['errors'])}")
            
            return data
        except Exception as e:
            logger.error(f"Error executing GraphQL query {query_id}: {e}\nTraceback:\n{traceback.format_exc()}")
            raise

class TwitterGraphQLResourcePlugin(TwitterBaseResourcePlugin):
    """
    Plugin for Twitter GraphQL API resource operations.
    
    This class implements the ResourcePlugin interface for Twitter GraphQL API operations,
    providing methods for initializing Twitter GraphQL clients, validating clients,
    and executing GraphQL queries.
    
    The plugin acts as a passthrough to Twitter's GraphQL API, allowing new GraphQL
    operations to be used without requiring code changes to the plugin.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin
        SCOPES (Dict[str, str]): Dictionary mapping scope names to descriptions
    """
    
    service_name = "twitter_graphql"
    
    SCOPES = {
        "twitter.graphql": "Permission to make GraphQL API calls to Twitter",
        "twitter.graphql.read": "Permission to make read-only GraphQL API calls",
        "twitter.graphql.write": "Permission to make write GraphQL API calls"
    }
    
    async def initialize_client(self, credentials: Dict[str, Any]) -> TwitterGraphQLClient:
        """
        Initialize Twitter GraphQL client with credentials.
        
        Creates a new TwitterGraphQLClient instance using the provided credentials.
        
        Args:
            credentials (Dict[str, Any]): The Twitter cookie credentials
            
        Returns:
            TwitterGraphQLClient: An initialized Twitter GraphQL client
            
        Raises:
            Exception: If the client cannot be initialized
        """
        try:
            return TwitterGraphQLClient(cookies=credentials)
        except Exception as e:
            logger.error(f"Error initializing Twitter GraphQL client: {e}")
            raise
    
    async def validate_client(self, client: TwitterGraphQLClient) -> bool:
        """
        Validate if the Twitter GraphQL client is still valid.
        
        Checks if the Twitter GraphQL client's credentials are still valid by making
        a lightweight API call to Twitter.
        
        Args:
            client (TwitterGraphQLClient): The client to validate
            
        Returns:
            bool: True if the client is valid, False otherwise
        """
        return await client.validate()
    
    async def execute_graphql_query(
        self, 
        client: TwitterGraphQLClient, 
        query_id: str, 
        variables: Optional[Dict[str, Any]] = None,
        features: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query using the client.
        
        This method acts as a passthrough to the client's execute_query method,
        forwarding the query to Twitter's GraphQL API.
        
        Args:
            client (TwitterGraphQLClient): The Twitter GraphQL client to use
            query_id (str): The GraphQL query ID to execute
            variables (Optional[Dict[str, Any]]): Variables to pass to the query
            features (Optional[Dict[str, Any]]): Feature flags to pass to the query
            method (str): HTTP method to use (GET or POST)
            
        Returns:
            Dict[str, Any]: The GraphQL response from Twitter
            
        Raises:
            ValueError: If the query fails or returns an error
            Exception: If any other error occurs during the operation
        """
        return await client.execute_query(query_id, variables, features, method)