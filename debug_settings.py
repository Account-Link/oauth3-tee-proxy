#!/usr/bin/env python
import os
from plugins.twitter.config import get_twitter_settings
from config import get_settings

# Print environment variables
print("Environment variables:")
for key, value in os.environ.items():
    if "TWITTER" in key:
        print(f"{key} = {value}")

# Get settings
twitter_settings = get_twitter_settings()
main_settings = get_settings()

# Print Twitter settings
print("\nTwitter settings:")
for key, value in twitter_settings.dict().items():
    print(f"{key} = {value}")

# Print main settings
print("\nMain settings:")
for key, value in main_settings.dict().items():
    if "TWITTER" in key:
        print(f"{key} = {value}")