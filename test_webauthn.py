#!/usr/bin/env python3
"""
Test script for WebAuthn login/register
"""

import json
import requests
import sys
import base64

def base64url_encode(data):
    """Encode bytes as base64url string"""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def test_login(username):
    """Test login flow with a username"""
    print(f"\n=== Testing login for user: {username} ===")
    
    # Step 1: Start authentication
    login_begin_url = "http://localhost:8000/auth/login/begin"
    login_begin_data = {
        "username": username
    }
    
    print(f"Sending login request to {login_begin_url} with data: {login_begin_data}")
    
    response = requests.post(
        login_begin_url,
        json=login_begin_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            # Try to parse as JSON
            print("Response headers:", response.headers)
            print("Response content type:", response.headers.get('content-type'))
            
            # Handle different content types
            if 'application/json' in response.headers.get('content-type', ''):
                options = response.json()
                print(f"Parsed response as JSON: {json.dumps(options, indent=2)}")
            else:
                text = response.text
                print(f"Response text (first 500 chars): {text[:500]}")
                
                # Try to parse as JSON anyway
                try:
                    options = json.loads(text)
                    print("Successfully parsed text as JSON:")
                    # Print key fields
                    if 'challenge' in options:
                        print(f"Challenge: {options['challenge']}")
                    if 'rpId' in options:
                        print(f"RP ID: {options['rpId']}")
                    if 'allowCredentials' in options:
                        print(f"Allow Credentials count: {len(options['allowCredentials'])}")
                        # Print first credential
                        if len(options['allowCredentials']) > 0:
                            print(f"First credential: {options['allowCredentials'][0]}")
                except json.JSONDecodeError as e:
                    print(f"Failed to parse as JSON: {e}")
        except Exception as e:
            print(f"Error processing response: {e}")
    else:
        try:
            print(f"Error response: {response.json()}")
        except Exception:
            print(f"Non-JSON error response: {response.text}")
    
    return response

def test_register(username, display_name=None):
    """Test registration flow with a username"""
    print(f"\n=== Testing registration for user: {username} ===")
    
    # Step 1: Start registration
    register_begin_url = "http://localhost:8000/auth/register/begin"
    register_begin_data = {
        "username": username
    }
    
    if display_name:
        register_begin_data["display_name"] = display_name
    
    print(f"Sending registration request to {register_begin_url} with data: {register_begin_data}")
    
    response = requests.post(
        register_begin_url,
        json=register_begin_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            options = response.json()
            print(f"Parsed response: {json.dumps(options, indent=2)}")
        except Exception as e:
            print(f"Error parsing response: {e}")
            print(f"Raw response: {response.text}")
    else:
        try:
            print(f"Error response: {response.json()}")
        except Exception:
            print(f"Non-JSON error response: {response.text}")
    
    return response

def main():
    if len(sys.argv) < 3:
        print("Usage: python test_webauthn.py [login|register] <username> [display_name]")
        return
    
    action = sys.argv[1].lower()
    username = sys.argv[2]
    display_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    if action == "login":
        test_login(username)
    elif action == "register":
        test_register(username, display_name)
    else:
        print(f"Unknown action: {action}. Use 'login' or 'register'.")

if __name__ == "__main__":
    main()