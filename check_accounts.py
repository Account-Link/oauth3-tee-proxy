#!/usr/bin/env python3
"""
Script to check Twitter accounts for a user.
"""

import sys
from database import SessionLocal

def check_twitter_accounts(user_id=None):
    """Check Twitter accounts for a specific user or all users."""
    # Import all models first to ensure relationships are properly loaded
    from models import User
    from plugins.twitter.models import TwitterAccount
    from plugins.telegram.models import TelegramAccount, TelegramChannel
    
    # Now open the database session
    db = SessionLocal()
    
    try:
        
        # Get user(s)
        query = db.query(User)
        if user_id:
            query = query.filter(User.id == user_id)
        
        users = query.all()
        
        if not users:
            print(f"No users found{' with ID ' + user_id if user_id else ''}")
            return
            
        print(f"Found {len(users)} users")
        
        for user in users:
            print(f"\nUser: {user.username} (ID: {user.id})")
            
            # Get Twitter accounts
            accounts = db.query(TwitterAccount).filter(TwitterAccount.user_id == user.id).all()
            
            if accounts:
                print(f"  Found {len(accounts)} Twitter accounts")
                for i, account in enumerate(accounts):
                    print(f"  Account {i+1}:")
                    print(f"    ID: {account.twitter_id}")
                    print(f"    Username: {account.username}")
                    print(f"    Display Name: {account.display_name}")
                    print(f"    Profile Image: {account.profile_image_url}")
                    print(f"    Cookie: {account.twitter_cookie[:10]}..." if account.twitter_cookie else "None")
                    print(f"    Created: {account.created_at}")
            else:
                print("  No Twitter accounts found for this user")
    finally:
        db.close()

if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    check_twitter_accounts(user_id)