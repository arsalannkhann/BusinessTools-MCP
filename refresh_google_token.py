#!/usr/bin/env python3
"""
Google OAuth Token Refresher
This script refreshes the expired Google OAuth token using the refresh token.
"""

import json
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

def refresh_google_token():
    """Refresh Google OAuth token"""
    token_file = "token.json"
    
    if not os.path.exists(token_file):
        print(f"❌ Token file {token_file} not found")
        return False
    
    try:
        # Load existing credentials
        print("📋 Loading existing credentials...")
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        # Create credentials object
        credentials = Credentials(
            token=token_data['token'],
            refresh_token=token_data['refresh_token'],
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=token_data['scopes']
        )
        
        print("🔄 Refreshing expired token...")
        
        # Refresh the token
        credentials.refresh(Request())
        
        # Save updated credentials
        updated_token = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "universe_domain": "googleapis.com",
            "account": "",
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        with open(token_file, 'w') as f:
            json.dump(updated_token, f, indent=2)
        
        print("✅ Token refreshed successfully!")
        print(f"🕐 New expiry: {credentials.expiry}")
        return True
        
    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
        return False

if __name__ == "__main__":
    print("🔑 Google Token Refresher")
    print("=" * 40)
    
    if refresh_google_token():
        print("\n🎉 Google authentication should now work!")
    else:
        print("\n⚠️  Token refresh failed. You may need to re-authenticate.")
        print("Run the Google OAuth flow again to get fresh credentials.")
