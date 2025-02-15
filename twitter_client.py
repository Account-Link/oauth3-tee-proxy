from twitter.account import Account
from typing import Optional, Dict
import json
import traceback

class TwitterClient:
    def __init__(self, cookie_dict: Dict):
        """Initialize Twitter client with cookie dictionary"""
        try:
            print(f"Initializing TwitterClient with cookies: {cookie_dict}")
            self.account = Account(cookies=cookie_dict)
        except Exception as e:
            print(f"Error initializing TwitterClient: {e}\nTraceback:\n{traceback.format_exc()}")
            raise
    
    @classmethod
    def from_cookie_string(cls, cookie_string: str) -> "TwitterClient":
        """Create TwitterClient from a cookie string"""
        try:
            print(f"Parsing cookie string: {cookie_string}")
            cookie_dict = json.loads(cookie_string)
            return cls(cookie_dict)
        except Exception as e:
            print(f"Error parsing cookie string: {e}\nTraceback:\n{traceback.format_exc()}")
            raise
    
    async def validate_cookie(self) -> bool:
        """Validate if the cookie is still valid"""
        try:
            print(self.account.bookmarks(limit=1))
            return True
        except Exception as e:
            print(f"Error validating cookie: {e}\nTraceback:\n{traceback.format_exc()}")
            raise
    
    async def get_user_id(self) -> str:
        """Get Twitter user ID from the account"""
        try:
            user_id = self.account.get_user_id()
            if not user_id:
                raise ValueError("Could not extract user ID from response")
            return user_id
        except Exception as e:
            print(f"Error getting user ID: {e}\nTraceback:\n{traceback.format_exc()}")
            raise
    
    async def post_tweet(self, text: str) -> str:
        """Post a tweet and return the tweet ID"""
        try:
            response = self.account.tweet(text)
            print(f"Tweet response: {response}")
            tweet_data = response.get('data', {})
            tweet_id = str(tweet_data.get('id_str') or tweet_data.get('id'))
            if not tweet_id:
                raise ValueError("Could not extract tweet ID from response")
            return tweet_id
        except Exception as e:
            print(f"Error posting tweet: {e}\nTraceback:\n{traceback.format_exc()}")
            raise