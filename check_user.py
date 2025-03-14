#!/usr/bin/env python3
"""
Simple script to check the user in the database using direct SQL
"""

import sqlite3
import sys

def list_users(conn):
    """List all users in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, display_name FROM users")
    users = cursor.fetchall()
    
    print(f"Found {len(users)} users:")
    for user in users:
        user_id, username, display_name = user
        print(f"- ID: {user_id}, Username: {username}, Display name: {display_name}")
        
        # Get passkeys for this user
        cursor.execute("SELECT id, credential_id, device_name, is_active FROM webauthn_credentials WHERE user_id = ?", (user_id,))
        passkeys = cursor.fetchall()
        print(f"  Has {len(passkeys)} passkeys:")
        for passkey in passkeys:
            passkey_id, credential_id, device_name, is_active = passkey
            print(f"  - ID: {passkey_id}, Credential ID: {credential_id}, Device: {device_name}, Active: {is_active}")

def find_user_by_username(conn, username):
    """Find a user by username."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, display_name FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if user:
        user_id, username, display_name = user
        print(f"Found user: ID: {user_id}, Username: {username}, Display name: {display_name}")
        
        # Get passkeys for this user
        cursor.execute("SELECT id, credential_id, device_name, is_active FROM webauthn_credentials WHERE user_id = ?", (user_id,))
        passkeys = cursor.fetchall()
        print(f"User has {len(passkeys)} passkeys:")
        for passkey in passkeys:
            passkey_id, credential_id, device_name, is_active = passkey
            print(f"- ID: {passkey_id}, Credential ID: {credential_id}, Device: {device_name}, Active: {is_active}")
        return user
    else:
        print(f"No user found with username '{username}'")
        return None

def main():
    # Connect to the database
    conn = sqlite3.connect('oauth3.db')
    
    if len(sys.argv) < 2:
        # List all users
        list_users(conn)
    else:
        # Find user by username
        username = sys.argv[1]
        user = find_user_by_username(conn, username)
        if not user:
            print(f"No user found with username '{username}'")
            # List available usernames
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users")
            usernames = [row[0] for row in cursor.fetchall()]
            print(f"Available usernames: {', '.join(usernames)}")
    
    conn.close()

if __name__ == "__main__":
    main()