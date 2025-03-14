# plugins/twitter/routes/v1_routes.py
"""
Twitter v1.1 API Routes
====================

This module implements HTTP routes for Twitter v1.1 API functionality in the
OAuth3 TEE Proxy. It defines the HTTP endpoints that clients can use to
interact with Twitter's v1.1 REST API via the proxy.

The TwitterV1Routes class implements the RoutePlugin interface and provides
routes for:
- Executing v1.1 API requests for any endpoint
- Supporting all standard HTTP methods (GET, POST, PUT, DELETE)

The routes act as a passthrough to Twitter's v1.1 API, allowing new API
operations to be supported without requiring code changes to the plugin.
"""

import logging
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Security, Body, Query, Path
from sqlalchemy.orm import Session

from database import get_db
from plugins.twitter.models import TwitterAccount
from models import OAuth2Token

# Lazily import verify_token_and_scopes to avoid circular imports
def get_verify_token_function():
    from oauth2_routes import verify_token_and_scopes
    return verify_token_and_scopes
from plugins import RoutePlugin

logger = logging.getLogger(__name__)

class TwitterV1Routes(RoutePlugin):
    """
    Plugin for Twitter v1.1 API routes.
    
    This class implements the RoutePlugin interface for Twitter v1.1 routes,
    providing HTTP endpoints for interacting with Twitter's v1.1 REST API
    through the TEE Proxy.
    
    The routes are mounted under the "/twitter/v1" prefix in the application.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin
    """
    
    def get_routers(self) -> Dict[str, APIRouter]:
        """
        Get all routers for this plugin.
        
        This is required by the RoutePlugin interface.
        
        Returns:
            Dict[str, APIRouter]: Dictionary mapping service names to routers
        """
        return {"twitter-v1": self.get_router()}
    
    service_name = "twitter/v1"
    
    def get_router(self) -> APIRouter:
        """
        Get the router for Twitter v1.1 API routes.
        
        Returns a FastAPI router with endpoints for accessing Twitter's v1.1 API.
        The router includes all standard HTTP methods for v1.1 API requests,
        supporting the full range of Twitter's v1.1 API operations.
        
        Returns:
            APIRouter: FastAPI router with Twitter v1.1 API routes
        """
        router = APIRouter(tags=["twitter", "v1"])
        
        @router.get("/{endpoint:path}")
        async def v1_get(
            endpoint: str = Path(..., description="The v1.1 API endpoint path"),
            response: Response = None,
            params: Optional[str] = Query(None, description="JSON-encoded query parameters"),
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["twitter.v1", "twitter.v1.read"]),
            db: Session = Depends(get_db)
        ):
            """
            Execute a Twitter v1.1 API GET request.
            
            This endpoint forwards a GET request to Twitter's v1.1 API, using the
            endpoint specified in the URL path and optional query parameters.
            
            Args:
                endpoint (str): The v1.1 API endpoint path
                params (Optional[str]): JSON-encoded query parameters
                token (OAuth2Token): The OAuth2 token for authorization
                db (Session): The database session
                
            Returns:
                Dict[str, Any]: The v1.1 API response from Twitter
            """
            return await _execute_v1_request(
                endpoint=endpoint,
                method="GET",
                params=params,
                data=None,
                json_data=None,
                token=token,
                db=db,
                response=response
            )
        
        @router.post("/{endpoint:path}")
        async def v1_post(
            endpoint: str = Path(..., description="The v1.1 API endpoint path"),
            response: Response = None,
            params: Optional[str] = Query(None, description="JSON-encoded query parameters"),
            body: Dict[str, Any] = Body({}, description="Request body"),
            is_json: bool = Query(True, description="Whether the body should be sent as JSON or form data"),
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["twitter.v1", "twitter.v1.write"]),
            db: Session = Depends(get_db)
        ):
            """
            Execute a Twitter v1.1 API POST request.
            
            This endpoint forwards a POST request to Twitter's v1.1 API, using the
            endpoint specified in the URL path and request body.
            
            Args:
                endpoint (str): The v1.1 API endpoint path
                params (Optional[str]): JSON-encoded query parameters
                body (Dict[str, Any]): Request body
                is_json (bool): Whether to send the body as JSON or form data
                token (OAuth2Token): The OAuth2 token for authorization
                db (Session): The database session
                
            Returns:
                Dict[str, Any]: The v1.1 API response from Twitter
            """
            return await _execute_v1_request(
                endpoint=endpoint,
                method="POST",
                params=params,
                data=None if is_json else body,
                json_data=body if is_json else None,
                token=token,
                db=db,
                response=response
            )
        
        @router.put("/{endpoint:path}")
        async def v1_put(
            endpoint: str = Path(..., description="The v1.1 API endpoint path"),
            response: Response = None,
            params: Optional[str] = Query(None, description="JSON-encoded query parameters"),
            body: Dict[str, Any] = Body({}, description="Request body"),
            is_json: bool = Query(True, description="Whether the body should be sent as JSON or form data"),
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["twitter.v1", "twitter.v1.write"]),
            db: Session = Depends(get_db)
        ):
            """
            Execute a Twitter v1.1 API PUT request.
            
            This endpoint forwards a PUT request to Twitter's v1.1 API, using the
            endpoint specified in the URL path and request body.
            
            Args:
                endpoint (str): The v1.1 API endpoint path
                params (Optional[str]): JSON-encoded query parameters
                body (Dict[str, Any]): Request body
                is_json (bool): Whether to send the body as JSON or form data
                token (OAuth2Token): The OAuth2 token for authorization
                db (Session): The database session
                
            Returns:
                Dict[str, Any]: The v1.1 API response from Twitter
            """
            return await _execute_v1_request(
                endpoint=endpoint,
                method="PUT",
                params=params,
                data=None if is_json else body,
                json_data=body if is_json else None,
                token=token,
                db=db,
                response=response
            )
        
        @router.delete("/{endpoint:path}")
        async def v1_delete(
            endpoint: str = Path(..., description="The v1.1 API endpoint path"),
            response: Response = None,
            params: Optional[str] = Query(None, description="JSON-encoded query parameters"),
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["twitter.v1", "twitter.v1.write"]),
            db: Session = Depends(get_db)
        ):
            """
            Execute a Twitter v1.1 API DELETE request.
            
            This endpoint forwards a DELETE request to Twitter's v1.1 API, using the
            endpoint specified in the URL path.
            
            Args:
                endpoint (str): The v1.1 API endpoint path
                params (Optional[str]): JSON-encoded query parameters
                token (OAuth2Token): The OAuth2 token for authorization
                db (Session): The database session
                
            Returns:
                Dict[str, Any]: The v1.1 API response from Twitter
            """
            return await _execute_v1_request(
                endpoint=endpoint,
                method="DELETE",
                params=params,
                data=None,
                json_data=None,
                token=token,
                db=db,
                response=response
            )
        
        async def _execute_v1_request(
            endpoint: str,
            method: str,
            params: Optional[str],
            data: Optional[Dict[str, Any]],
            json_data: Optional[Dict[str, Any]],
            token: OAuth2Token,
            db: Session,
            response: Response
        ):
            """
            Helper method to execute a v1.1 API request.
            
            This method handles the common logic for all v1.1 API requests,
            retrieving the Twitter account, initializing the v1.1 client, and
            executing the request.
            
            Args:
                endpoint (str): The v1.1 API endpoint path
                method (str): HTTP method to use (GET, POST, PUT, DELETE)
                params (Optional[str]): JSON-encoded query parameters
                data (Optional[Dict[str, Any]]): Form data for POST/PUT requests
                json_data (Optional[Dict[str, Any]]): JSON data for POST/PUT requests
                token (OAuth2Token): The OAuth2 token for authorization
                db (Session): The database session
                response (Response): The FastAPI response object for setting headers
                
            Returns:
                Dict[str, Any]: The v1.1 API response from Twitter
                
            Raises:
                HTTPException: If an error occurs during request execution
            """
            try:
                # Get the Twitter account associated with the token
                twitter_account = db.query(TwitterAccount).filter(
                    TwitterAccount.user_id == token.user_id
                ).first()
                
                if not twitter_account:
                    logger.error(f"No Twitter account found for user {token.user_id}")
                    raise HTTPException(status_code=404, detail="Twitter account not found")
                
                # Import required plugins
                from plugin_manager import plugin_manager
                twitter_auth = plugin_manager.create_authorization_plugin("twitter_cookie")
                twitter_v1 = plugin_manager.create_resource_plugin("twitter_v1")
                
                if not twitter_auth or not twitter_v1:
                    raise HTTPException(
                        status_code=500,
                        detail="Required Twitter plugins not available"
                    )
                
                # Parse params if they are provided as a string
                parsed_params = None
                if params is not None:
                    try:
                        parsed_params = json.loads(params)
                    except json.JSONDecodeError:
                        raise HTTPException(
                            status_code=400, 
                            detail="Invalid JSON in 'params' parameter"
                        )
                
                # Initialize the v1.1 client
                credentials = twitter_auth.credentials_from_string(twitter_account.twitter_cookie)
                client = await twitter_v1.initialize_client(credentials)
                
                # Execute the v1.1 API request
                result = await twitter_v1.execute_v1_request(
                    client=client,
                    endpoint=endpoint,
                    method=method,
                    params=parsed_params,
                    data=data,
                    json_data=json_data
                )
                
                # Set response headers if needed
                if response:
                    response.headers["X-Twitter-API-Version"] = "1.1"
                
                return result
                
            except ValueError as e:
                logger.error(f"Twitter v1.1 API request error: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"Error executing Twitter v1.1 API request: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal server error")
        
        return router