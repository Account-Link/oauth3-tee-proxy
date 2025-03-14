# plugins/twitter/routes/graphql_routes.py
"""
Twitter GraphQL Routes
====================

This module implements HTTP routes for Twitter GraphQL functionality in the
OAuth3 TEE Proxy. It defines the HTTP endpoints that clients can use to
interact with Twitter's private GraphQL API via the proxy.

The TwitterGraphQLRoutes class implements the RoutePlugin interface and provides
routes for:
- Executing GraphQL queries by query ID
- Supporting both GET and POST methods for GraphQL queries
- Providing a GraphQL playground UI for testing queries

The routes act as a passthrough to Twitter's GraphQL API, allowing new GraphQL
operations to be supported without requiring code changes to the plugin.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Security, Body, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from plugins.twitter.models import TwitterAccount
from models import OAuth2Token, User
from plugins import RoutePlugin
from plugin_manager import plugin_manager

# Import UI provider
from .graphql_ui import twitter_graphql_ui

# Register UI provider with plugin manager
plugin_manager._plugin_ui_providers["twitter/graphql"] = twitter_graphql_ui

# Lazily import verify_token_and_scopes to avoid circular imports
def get_verify_token_function():
    from oauth2_routes import verify_token_and_scopes
    return verify_token_and_scopes

logger = logging.getLogger(__name__)

class TwitterGraphQLRoutes(RoutePlugin):
    """
    Plugin for Twitter GraphQL API routes.
    
    This class implements the RoutePlugin interface for Twitter GraphQL routes,
    providing HTTP endpoints that let clients execute GraphQL queries against
    Twitter's API via the proxy.
    
    The routes are mounted under the "/twitter/graphql" prefix in the application.
    
    Class Attributes:
        service_name (str): The unique identifier for this plugin
    """
    
    service_name = "twitter/graphql"
    
    def get_routers(self) -> Dict[str, APIRouter]:
        """
        Get all routers for this plugin.
        
        This is required by the RoutePlugin interface.
        
        Returns:
            Dict[str, APIRouter]: Dictionary mapping service names to routers
        """
        return {"twitter-graphql": self.get_router()}
    
    def get_auth_requirements(self) -> dict:
        """
        Define authentication requirements for Twitter GraphQL routes.
        
        This method specifies which authentication types are required for
        different GraphQL route patterns.
        
        Returns:
            dict: Mapping of route patterns to required authentication types
        """
        return {
            # GraphQL playground requires passkey authentication
            "/playground": ["passkey"],
            
            # GraphQL query endpoints allow both API token and passkey authentication
            "/*": ["api", "passkey"]
        }
        
    def get_jwt_policy_scopes(self) -> dict:
        """
        Define JWT policy to scopes mapping for GraphQL plugin.
        
        This method defines JWT policies specific to GraphQL operations with
        pre-defined sets of scopes.
        
        Returns:
            dict: Mapping of policy names to sets of scopes
        """
        return {
            "graphql-read-only": {"twitter.graphql.read"},
            "graphql-write-only": {"twitter.graphql.write"},
            "graphql-full-access": {"twitter.graphql", "twitter.graphql.read", "twitter.graphql.write"}
        }
    
    def get_router(self) -> APIRouter:
        """
        Get the router for Twitter GraphQL routes.
        
        Returns a FastAPI router with endpoints for accessing Twitter's GraphQL API.
        The router includes both GET and POST methods for GraphQL queries, supporting
        the full range of Twitter's private GraphQL operations.
        
        Returns:
            APIRouter: FastAPI router with Twitter GraphQL routes
        """
        router = APIRouter(tags=["twitter", "graphql"])
        
        # Add GraphQL Playground route
        @router.get("/playground", response_class=HTMLResponse)
        async def graphql_playground(request: Request, db: Session = Depends(get_db)):
            """
            Interactive playground for testing Twitter GraphQL queries.
            
            This page provides a user interface for testing Twitter GraphQL queries through
            the OAuth3 TEE Proxy. It allows selecting from predefined operations or entering
            custom query IDs, and supports both GET and POST methods.
            """
            user_id = request.session.get("user_id")
            if not user_id:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url="/auth/login")
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                request.session.clear()
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url="/auth/login")
            
            # Get active OAuth2 tokens with appropriate scopes
            oauth2_tokens = db.query(OAuth2Token).filter(
                OAuth2Token.user_id == user_id,
                OAuth2Token.is_active == True,
                OAuth2Token.expires_at > datetime.utcnow(),
                OAuth2Token.scopes.contains("twitter.graphql")
            ).all()
            
            # Import the Twitter GraphQL operations
            from plugins.twitter.policy import TWITTER_GRAPHQL_OPERATIONS
            
            # Use the UI provider to render the playground
            return twitter_graphql_ui.render_graphql_playground(
                request, 
                oauth2_tokens, 
                TWITTER_GRAPHQL_OPERATIONS
            )
        
        @router.get("/{query_id}")
        async def execute_graphql_get(
            query_id: str,
            variables: Optional[str] = Query(None),
            features: Optional[str] = Query(None),
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["twitter.graphql", "twitter.graphql.read"]),
            db: Session = Depends(get_db)
        ):
            """
            Execute a Twitter GraphQL query using GET method.
            
            This endpoint forwards a GraphQL query to Twitter's API, using the query ID
            specified in the URL path and optional variables and features as query parameters.
            
            Args:
                query_id (str): The GraphQL query ID to execute
                variables (Optional[str]): JSON-encoded variables to pass to the query
                features (Optional[str]): JSON-encoded feature flags to pass to the query
                token (OAuth2Token): The OAuth2 token for authorization
                db (Session): The database session
                
            Returns:
                Dict[str, Any]: The GraphQL response from Twitter
            """
            return await self._execute_graphql_query(
                query_id=query_id,
                variables=variables,
                features=features,
                method="GET",
                token=token,
                db=db
            )
        
        @router.post("/{query_id}")
        async def execute_graphql_post(
            query_id: str,
            body: Dict[str, Any] = Body({}),
            token: OAuth2Token = Security(get_verify_token_function(), scopes=["twitter.graphql", "twitter.graphql.write"]),
            db: Session = Depends(get_db)
        ):
            """
            Execute a Twitter GraphQL query using POST method.
            
            This endpoint forwards a GraphQL query to Twitter's API, using the query ID
            specified in the URL path and request body for variables and features.
            
            Args:
                query_id (str): The GraphQL query ID to execute
                body (Dict[str, Any]): Request body containing variables and features
                token (OAuth2Token): The OAuth2 token for authorization
                db (Session): The database session
                
            Returns:
                Dict[str, Any]: The GraphQL response from Twitter
            """
            variables = body.get("variables")
            features = body.get("features")
            
            return await self._execute_graphql_query(
                query_id=query_id,
                variables=variables,
                features=features,
                method="POST",
                token=token,
                db=db
            )
        
        async def _execute_graphql_query(
            query_id: str,
            variables: Optional[str],
            features: Optional[str],
            method: str,
            token: OAuth2Token,
            db: Session
        ):
            """
            Helper method to execute a GraphQL query.
            
            This method handles the common logic for both GET and POST GraphQL queries,
            retrieving the Twitter account, initializing the GraphQL client, and
            executing the query.
            
            Args:
                query_id (str): The GraphQL query ID to execute
                variables (Optional[str]): JSON-encoded variables or dict to pass to the query
                features (Optional[str]): JSON-encoded feature flags or dict to pass to the query
                method (str): HTTP method to use (GET or POST)
                token (OAuth2Token): The OAuth2 token for authorization
                db (Session): The database session
                
            Returns:
                Dict[str, Any]: The GraphQL response from Twitter
                
            Raises:
                HTTPException: If an error occurs during query execution
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
                twitter_graphql = plugin_manager.create_resource_plugin("twitter_graphql")
                
                if not twitter_auth or not twitter_graphql:
                    raise HTTPException(
                        status_code=500,
                        detail="Required Twitter plugins not available"
                    )
                
                # Check policy access for the requested query_id
                from plugins.twitter.policy import verify_policy_access, get_operation_info
                
                # Get the policy from the Twitter account
                policy = twitter_account.policy
                
                # Verify policy access for the requested query ID
                operation_info = get_operation_info(query_id)
                if not operation_info:
                    logger.warning(f"Unknown GraphQL query ID: {query_id}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Unknown GraphQL query ID: {query_id}"
                    )
                
                # Check if the operation is allowed by the policy
                if not verify_policy_access(query_id, policy):
                    logger.warning(
                        f"Policy violation: User {token.user_id} attempted to execute "
                        f"unauthorized GraphQL query {query_id} ({operation_info.get('operation_name', 'unknown')})"
                    )
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Access to operation '{operation_info.get('operation_name', query_id)}' is not allowed by policy"
                    )
                
                # Parse variables and features if they are strings
                parsed_variables = None
                if variables is not None:
                    if isinstance(variables, str):
                        import json
                        try:
                            parsed_variables = json.loads(variables)
                        except json.JSONDecodeError:
                            raise HTTPException(
                                status_code=400, 
                                detail="Invalid JSON in 'variables' parameter"
                            )
                    else:
                        parsed_variables = variables
                
                parsed_features = None
                if features is not None:
                    if isinstance(features, str):
                        import json
                        try:
                            parsed_features = json.loads(features)
                        except json.JSONDecodeError:
                            raise HTTPException(
                                status_code=400, 
                                detail="Invalid JSON in 'features' parameter"
                            )
                    else:
                        parsed_features = features
                
                # Initialize the GraphQL client
                credentials = twitter_auth.credentials_from_string(twitter_account.twitter_cookie)
                client = await twitter_graphql.initialize_client(credentials)
                
                # Execute the GraphQL query
                result = await twitter_graphql.execute_graphql_query(
                    client=client,
                    query_id=query_id,
                    variables=parsed_variables,
                    features=parsed_features,
                    method=method
                )
                
                return result
                
            except ValueError as e:
                logger.error(f"GraphQL query error: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"Error executing GraphQL query: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal server error")
        
        return router