from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./oauth3.db"
    
    # Session Management
    SESSION_EXPIRY_HOURS: int = 24
    
    # Post Key Settings
    POST_KEY_MAX_PER_ACCOUNT: int = 100
    
    # Safety Filter Settings
    SAFETY_FILTER_ENABLED: bool = True
    SAFETY_FILTER_MAX_TOKENS: int = 280
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 