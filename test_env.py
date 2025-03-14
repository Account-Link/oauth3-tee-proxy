#!/usr/bin/env python3
"""
Test script to verify environment variables are loaded correctly.
"""

import os
import sys

def main():
    try:
        from dotenv import load_dotenv
        print("Found python-dotenv, loading .env file")
        load_dotenv()
    except ImportError:
        print("WARNING: python-dotenv not installed, .env file will not be loaded explicitly")
    
    # Check if the variables are in the environment
    twitter_key = os.environ.get('TWITTER_CONSUMER_KEY')
    twitter_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
    
    print(f"TWITTER_CONSUMER_KEY: {twitter_key or 'NOT SET'}")
    print(f"TWITTER_CONSUMER_SECRET: {'SET' if twitter_secret else 'NOT SET'}")
    
    if twitter_key and twitter_secret:
        print("SUCCESS: Twitter OAuth credentials are properly set in the environment")
    else:
        print("ERROR: Twitter OAuth credentials are missing")
        
        # Try to load from .env file manually
        try:
            env_file = '.env'
            print(f"Attempting to read {env_file}:")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if 'TWITTER' in key:
                            if key == 'TWITTER_CONSUMER_KEY':
                                print(f"  Found TWITTER_CONSUMER_KEY in .env: {value}")
                            elif key == 'TWITTER_CONSUMER_SECRET':
                                print(f"  Found TWITTER_CONSUMER_SECRET in .env: {'*' * len(value)}")
                            else:
                                print(f"  Found {key} in .env file")
        except Exception as e:
            print(f"Error reading .env file: {e}")
    
    # Try to import pydantic settings
    try:
        from config import get_settings
        settings = get_settings()
        print("\nFrom pydantic settings:")
        print(f"settings.TWITTER_CONSUMER_KEY: {settings.TWITTER_CONSUMER_KEY or 'NOT SET'}")
        print(f"settings.TWITTER_CONSUMER_SECRET: {'SET' if settings.TWITTER_CONSUMER_SECRET else 'NOT SET'}")
    except Exception as e:
        print(f"Error loading pydantic settings: {e}")

if __name__ == "__main__":
    main()