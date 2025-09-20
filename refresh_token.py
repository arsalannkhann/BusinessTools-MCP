#!/usr/bin/env python3
"""Script to manually refresh Google OAuth token"""

import json
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Load token
token_path = "token.json"
if not os.path.exists(token_path):
    print(f"Token file {token_path} not found")
    exit(1)

with open(token_path, 'r') as f:
    token_data = json.load(f)

# Create credentials
credentials = Credentials.from_authorized_user_info(token_data)

print(f"Token valid: {credentials.valid}")
print(f"Token expired: {credentials.expired}")
print(f"Has refresh token: {bool(credentials.refresh_token)}")

if credentials.expired and credentials.refresh_token:
    print("Refreshing expired token...")
    try:
        credentials.refresh(Request())
        print("✅ Token refreshed successfully")
        
        # Save refreshed token
        with open(token_path, 'w') as f:
            f.write(credentials.to_json())
        print(f"✅ Saved refreshed token to {token_path}")
        
    except Exception as e:
        print(f"❌ Failed to refresh token: {e}")
        exit(1)
        
elif credentials.valid:
    print("✅ Token is already valid")
else:
    print("❌ Token is invalid and cannot be refreshed")
    exit(1)

print("\nToken status after refresh:")
print(f"Valid: {credentials.valid}")
print(f"Expired: {credentials.expired}")
if hasattr(credentials, 'expiry') and credentials.expiry:
    print(f"Expires at: {credentials.expiry}")
