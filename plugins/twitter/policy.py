# plugins/twitter/policy.py
"""
Twitter Policy Module
====================

This module defines policy controls for Twitter API access, allowing fine-grained
permissions for which GraphQL queries and operations clients are allowed to perform.

The policy system provides:
- A comprehensive registry of all available Twitter GraphQL operations
- Categorization of operations as read or write operations
- Policy verification functions to validate access based on user context
- Default policy templates that cover common use cases
"""

import logging
from typing import Dict, Any, List, Optional, Set, Union
import json

logger = logging.getLogger(__name__)

# Define all available Twitter GraphQL operations with their IDs
# This is a comprehensive registry of operations from Twitter's GraphQL API
TWITTER_GRAPHQL_OPERATIONS = {
    # Authentication
    "r7VUmxbfqNkx7uwjgONSNw": {
        "operation_name": "AuthenticatePeriscope",
        "method": "GET",
        "category": "read",
        "description": "Authenticates with the Periscope service"
    },
    "PFIxTk8owMoZgiMccP0r4g": {
        "operation_name": "getAltTextPromptPreference",
        "method": "GET",
        "category": "read",
        "description": "Retrieves the alt text prompt preference settings"
    },
    "aQKrduk_DA46XfOQDkcEng": {
        "operation_name": "updateAltTextPromptPreference",
        "method": "POST",
        "category": "write",
        "description": "Updates the alt text prompt preference settings"
    },
    
    # Tweets and Timeline
    "pROR-yRiBVsEjJyHt3fvhg": {
        "operation_name": "BakeryQuery",
        "method": "GET",
        "category": "read",
        "description": "Query for Bakery service"
    },
    "3dxpcdWUUMnHzzAkQKmYbg": {
        "operation_name": "BlockedAccountsAll",
        "method": "GET",
        "category": "read",
        "description": "Retrieves all blocked accounts"
    },
    "oPHs3ydu7ZOOy2f02soaPA": {
        "operation_name": "UserTweets",
        "method": "GET",
        "category": "read",
        "description": "Fetches tweets from a specific user"
    },
    "UYy4T67XpYXgWKOafKXB_A": {
        "operation_name": "CreateTweet",
        "method": "POST",
        "category": "write",
        "description": "Creates a new tweet"
    },
    "VaenaVgh5q5ih7kvyVjgtg": {
        "operation_name": "DeleteTweet",
        "method": "POST",
        "category": "write",
        "description": "Deletes a tweet"
    },
    "lI07N6Otwv1PhnEgXILM7A": {
        "operation_name": "FavoriteTweet",
        "method": "POST",
        "category": "write",
        "description": "Favorites/likes a tweet"
    },
    "ojPdsZsimiJrUGLR1sjUtA": {
        "operation_name": "RetweetTweet",
        "method": "POST",
        "category": "write",
        "description": "Retweets a tweet"
    },
    "ZYKSe-w7KEslx3JhSIk5LA": {
        "operation_name": "UnfavoriteTweet",
        "method": "POST",
        "category": "write",
        "description": "Unfavorites/unlikes a tweet"
    },
    "iQtK4dl5hBmXewYZuEOKVw": {
        "operation_name": "UnretweetTweet",
        "method": "POST",
        "category": "write",
        "description": "Unretweets a tweet"
    },
    
    # User data
    "8sXVIfHXt5J5Mk5nY6jF0w": {
        "operation_name": "UserByScreenName",
        "method": "GET",
        "category": "read",
        "description": "Fetches user data by screen name"
    },
    "BS5XvxjJzKnT9B1vdQNuVQ": {
        "operation_name": "UserByRestId",
        "method": "GET",
        "category": "read",
        "description": "Fetches user data by REST ID"
    },
    "3JNH4e9dq1EbVEjbH17CRw": {
        "operation_name": "UserTimeline",
        "method": "GET",
        "category": "read",
        "description": "Fetches a user's timeline"
    },
    
    # Timelines
    "oDN9CSPdf7hHMJkAoTw9Ww": {
        "operation_name": "HomeTimeline",
        "method": "GET",
        "category": "read",
        "description": "Fetches the home timeline"
    },
    "qibjzEWwVSl0sSV8-VlR6Q": {
        "operation_name": "HomeLatestTimeline",
        "method": "GET",
        "category": "read",
        "description": "Fetches the latest tweets for the home timeline"
    },
    "f_BkJh4mwCPQSh0jmJZzug": {
        "operation_name": "SearchTimeline",
        "method": "GET",
        "category": "read",
        "description": "Searches for tweets"
    },
    "P0Q1RWRCWxVEJjkU7rzG3g": {
        "operation_name": "TweetDetail",
        "method": "GET",
        "category": "read",
        "description": "Fetches detailed information about a tweet"
    },
    "vFmPRx4zYD-4iWYbOdYs1A": {
        "operation_name": "ListLatestTweetsTimeline",
        "method": "GET",
        "category": "read",
        "description": "Fetches the latest tweets from a list"
    },
    
    # Social
    "UqGF_XBnacQeigT-d0qJ0A": {
        "operation_name": "FollowersYouKnow",
        "method": "GET",
        "category": "read",
        "description": "Fetches followers you know"
    },
    
    # Profile and Account
    "pCFxFqsnO8IYFGREUYBh0Q": {
        "operation_name": "GetUserClaims",
        "method": "GET",
        "category": "read",
        "description": "Gets user claims/verified status"
    },
    "BYWA-v2zXm7dfhMbO-dPJw": {
        "operation_name": "ProfileSpotlightsQuery",
        "method": "GET",
        "category": "read",
        "description": "Gets profile spotlights"
    },
    "NTq79TuSz5GrVLKLBWqKJg": {
        "operation_name": "CommunitiesTabQuery",
        "method": "GET",
        "category": "read",
        "description": "Gets communities tab data"
    },
    
    # Notifications and Messages
    "JpDrL4k4d4A6FQ-RvrBJrw": {
        "operation_name": "NotificationTimeline",
        "method": "GET",
        "category": "read",
        "description": "Fetches notification timeline"
    },
    "cAQq4LxBHZnvJ9iTDgP1GA": {
        "operation_name": "DMConversationsList",
        "method": "GET",
        "category": "read",
        "description": "Fetches DM conversations list"
    },
    "e1MYROkq6xpKz8rrVbRPGg": {
        "operation_name": "DMMessageCreate",
        "method": "POST",
        "category": "write",
        "description": "Creates a DM message"
    },
    "tO0maWw7RKVKRMzfnU9jgw": {
        "operation_name": "UsersLookup",
        "method": "GET",
        "category": "read",
        "description": "Looks up multiple users"
    },
    
    # This can be extended with all other Twitter GraphQL operations
    # as more operations are discovered and documented
}

class TwitterPolicy:
    """
    Twitter policy control for GraphQL operations.
    
    This class defines which GraphQL operations are allowed for a specific
    authentication context. It provides methods to verify if an operation
    is allowed based on the policy configuration.
    
    Attributes:
        allowed_operations (Set[str]): Set of allowed operation query IDs
        allowed_categories (Set[str]): Set of allowed operation categories
    """
    
    def __init__(
        self, 
        allowed_operations: Optional[List[str]] = None,
        allowed_categories: Optional[List[str]] = None
    ):
        """
        Initialize the policy with allowed operations and categories.
        
        Args:
            allowed_operations (Optional[List[str]]): List of allowed operation query IDs
            allowed_categories (Optional[List[str]]): List of allowed operation categories
        """
        self.allowed_operations = set(allowed_operations or [])
        self.allowed_categories = set(allowed_categories or [])
    
    def is_operation_allowed(self, query_id: str) -> bool:
        """
        Check if a specific operation is allowed by the policy.
        
        Args:
            query_id (str): The query ID of the operation to check
            
        Returns:
            bool: True if the operation is allowed, False otherwise
        """
        # If the operation is specifically allowed
        if query_id in self.allowed_operations:
            return True
        
        # If the operation's category is allowed
        operation_info = TWITTER_GRAPHQL_OPERATIONS.get(query_id)
        if operation_info and operation_info.get("category") in self.allowed_categories:
            return True
            
        return False
    
    @classmethod
    def from_dict(cls, policy_dict: Dict[str, Any]) -> "TwitterPolicy":
        """
        Create a TwitterPolicy from a dictionary representation.
        
        Args:
            policy_dict (Dict[str, Any]): Dictionary with policy configuration
            
        Returns:
            TwitterPolicy: The policy object
        """
        return cls(
            allowed_operations=policy_dict.get("allowed_operations", []),
            allowed_categories=policy_dict.get("allowed_categories", [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the policy to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the policy
        """
        return {
            "allowed_operations": list(self.allowed_operations),
            "allowed_categories": list(self.allowed_categories)
        }
    
    @classmethod
    def get_default_policy(cls) -> "TwitterPolicy":
        """
        Get the default policy that allows all operations.
        
        Returns:
            TwitterPolicy: Default policy allowing all operations
        """
        return cls(
            allowed_operations=list(TWITTER_GRAPHQL_OPERATIONS.keys()),
            allowed_categories=["read", "write"]
        )
    
    @classmethod
    def get_read_only_policy(cls) -> "TwitterPolicy":
        """
        Get a read-only policy that allows only read operations.
        
        Returns:
            TwitterPolicy: Policy allowing only read operations
        """
        return cls(allowed_categories=["read"])
    
    @classmethod
    def get_write_only_policy(cls) -> "TwitterPolicy":
        """
        Get a write-only policy that allows only write operations.
        
        Returns:
            TwitterPolicy: Policy allowing only write operations
        """
        return cls(allowed_categories=["write"])

def verify_policy_access(query_id: str, policy: Union[TwitterPolicy, Dict[str, Any]]) -> bool:
    """
    Verify if access to a specific operation is allowed by the policy.
    
    This is a utility function that can be used to check if an operation
    is allowed based on a policy, which can be either a TwitterPolicy object
    or a dictionary representation of a policy.
    
    Args:
        query_id (str): The query ID of the operation to check
        policy (Union[TwitterPolicy, Dict[str, Any]]): The policy to check against
            
    Returns:
        bool: True if the operation is allowed, False otherwise
    """
    if isinstance(policy, dict):
        policy = TwitterPolicy.from_dict(policy)
        
    return policy.is_operation_allowed(query_id)

# Operation category helpers
def get_read_operations() -> List[str]:
    """
    Get a list of all read operation query IDs.
    
    Returns:
        List[str]: List of read operation query IDs
    """
    return [
        query_id for query_id, info in TWITTER_GRAPHQL_OPERATIONS.items()
        if info.get("category") == "read"
    ]

def get_write_operations() -> List[str]:
    """
    Get a list of all write operation query IDs.
    
    Returns:
        List[str]: List of write operation query IDs
    """
    return [
        query_id for query_id, info in TWITTER_GRAPHQL_OPERATIONS.items()
        if info.get("category") == "write"
    ]

def get_operation_info(query_id: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a specific operation.
    
    Args:
        query_id (str): The query ID to get information for
        
    Returns:
        Optional[Dict[str, Any]]: Operation information or None if not found
    """
    return TWITTER_GRAPHQL_OPERATIONS.get(query_id)