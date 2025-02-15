from enum import Enum
from typing import Tuple

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