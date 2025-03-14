from enum import Enum
from typing import Dict, Any, Optional, Tuple
import jwt
from datetime import datetime, timedelta
import os
import secrets

class SafetyLevel(Enum):
    STRICT = "strict"
    MODERATE = "moderate"
    MINIMAL = "minimal"

class SafetyFilter:
    def __init__(self, level: SafetyLevel = SafetyLevel.MODERATE):
        self.level = level
        self._init_patterns()
    
    def _init_patterns(self):
        # Basic patterns that might indicate unsafe content
        # These would need to be expanded based on specific requirements
        self.patterns = {
            SafetyLevel.STRICT: [
                r'(hate|violent|explicit)',
                r'(spam|scam|fraud)',
                r'(private.*information)',
            ],
            SafetyLevel.MODERATE: [
                r'(spam|scam)',
                r'(explicit)',
            ],
            SafetyLevel.MINIMAL: [
                r'(spam)',
            ]
        }
    
    async def check_tweet(self, text: str) -> Tuple[bool, str]:
        """
        Checks if tweet content is safe to post.
        Returns (is_safe, reason_if_unsafe)
        """
        if not text.strip():
            return False, "Tweet cannot be empty"
        
        if len(text) > 280:
            return False, "Tweet exceeds maximum length"
        
        # Apply patterns based on safety level
        import re
        patterns = self.patterns[self.level]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False, f"Content matches restricted pattern: {pattern}"
        
        return True, "" 

# JWT secret key - in production, get from environment variable
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "supersecretkey")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2 hours

def create_jwt_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token with the given data and expiration time.
    
    Args:
        data (Dict[str, Any]): The data to encode in the token
        expires_delta (Optional[timedelta]): Optional expiration time delta
        
    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    
    # Add jti (JWT ID) for token revocation
    to_encode.update({"jti": secrets.token_hex(16)})
    
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token and return the payload.
    
    Args:
        token (str): The JWT token to decode
        
    Returns:
        Optional[Dict[str, Any]]: The decoded token payload, or None if decoding fails
    """
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None