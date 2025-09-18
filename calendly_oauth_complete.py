#!/usr/bin/env python3
"""
Calendly OAuth Token Generator with proper callback server
Matches your configured redirect URI: http://localhost:5000/
"""

import os
import requests
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import json

# Your Calendly credentials
CLIENT_ID = "bMqjtcRI8cO7leco8kmTXFc1RosnL-Mvq05VIJ3ebeg"
CLIENT_SECRET = "s3g8ePlt6joiJhkRqh_2RPx8YEKmP1h8gdwp9CkO66U"
REDIRECT_URI = "http://localhost:5000/"

# Calendly OAuth URLs
AUTHORIZATION_URL = "https://auth.calendly.com/oauth/authorize"
TOKEN_URL = "https://auth.calendly.com/oauth/token"

# Global variable to store the authorization code
auth_code = None
server_running = True

class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback"""
    
    def do_GET(self):
        global auth_code, server_running
        
        # Parse the authorization code from the callback URL
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'code' in params:
            auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            response_html = f"""
            <html>
            <head><title>Calendly OAuth Success</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2 style="color: green;">✅ Calendly Authorization Successful!</h2>
            <p>Authorization code received successfully.</p>
            <p>You can close this window and return to the terminal.</p>
            <p style="color: #666; font-size: 12px;">Code: {auth_code}</p>
            <script>setTimeout(function(){{window.close();}}, 5000);</script>
            </body>
            </html>
            """
            self.wfile.write(response_html.encode('utf-8'))
            server_running = False
        elif 'error' in params:
            error = params.get('error', ['Unknown error'])[0]
            error_desc = params.get('error_description', [''])[0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
            <html>
            <head><title>Calendly OAuth Error</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2 style="color: red;">❌ Calendly Authorization Failed</h2>
            <p><strong>Error:</strong> {error}</p>
            <p><strong>Description:</strong> {error_desc}</p>
            <p>Please try again or check your Calendly app configuration.</p>
            </body>
            </html>
            """.encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
            <html>
            <head><title>Calendly OAuth</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2>Calendly OAuth Callback</h2>
            <p>Waiting for authorization...</p>
            </body>
            </html>
            """)
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_callback_server():
    """Start the local callback server on port 5000"""
    try:
        server = HTTPServer(('localhost', 5000), CallbackHandler)
        print("✅ Callback server started on http://localhost:5000/")
        
        def run_server():
            global server_running
            while server_running:
                try:
                    server.handle_request()
                except:
                    break
            try:
                server.server_close()
            except:
                pass
        
        thread = threading.Thread(target=run_server)
        thread.daemon = True
        thread.start()
        return server
    except OSError as e:
        if "Address already in use" in str(e):
            print("❌ Port 5000 is already in use. Please stop any running Flask apps and try again.")
            return None
        else:
            raise

def get_authorization_url():
    """Generate the Calendly authorization URL"""
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': 'default'
    }
    
    url = AUTHORIZATION_URL + '?' + urllib.parse.urlencode(params)
    return url

def exchange_code_for_token(auth_code):
    """Exchange authorization code for access token"""
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': auth_code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        print("🔄 Exchanging authorization code for access token...")
        response = requests.post(TOKEN_URL, data=data, headers=headers)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data
        else:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error exchanging code for token: {e}")
        return None

def test_token(access_token):
    """Test the access token by making a simple API call"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        print("🧪 Testing access token with Calendly API...")
        response = requests.get('https://api.calendly.com/users/me', headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            return user_data
        else:
            print(f"❌ Token test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error testing token: {e}")
        return None

def update_env_files(access_token, refresh_token=None):
    """Update both .env and .env.example files with the new access token"""
    try:
        files_to_update = ['.env.example']
        if os.path.exists('.env'):
            files_to_update.append('.env')
        else:
            # Create .env from .env.example
            if os.path.exists('.env.example'):
                with open('.env.example', 'r') as f:
                    content = f.read()
                with open('.env', 'w') as f:
                    f.write(content)
                files_to_update.append('.env')
        
        for file_path in files_to_update:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Update the access token
            if 'CALENDLY_ACCESS_TOKEN=' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('CALENDLY_ACCESS_TOKEN='):
                        lines[i] = f'CALENDLY_ACCESS_TOKEN={access_token}'
                        break
                content = '\n'.join(lines)
            else:
                content += f'\nCALENDLY_ACCESS_TOKEN={access_token}\n'
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Updated {file_path} with access token")
        
        if refresh_token:
            print(f"💡 Refresh token (save this securely): {refresh_token}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating env files: {e}")
        return False

def main():
    """Main function to run the OAuth flow"""
    global auth_code, server_running
    
    print("🚀 Calendly OAuth Token Generator")
    print("=" * 50)
    print(f"Client ID: {CLIENT_ID}")
    print(f"Redirect URI: {REDIRECT_URI}")
    print()
    
    print("1. Starting callback server...")
    server = start_callback_server()
    if not server:
        return
    
    time.sleep(2)  # Give server time to start
    
    print("2. Opening Calendly authorization URL...")
    auth_url = get_authorization_url()
    print(f"   URL: {auth_url}")
    print()
    
    try:
        webbrowser.open(auth_url)
        print("✅ Browser opened. Please complete authorization in Calendly.")
    except:
        print("⚠️  Could not open browser automatically.")
        print("   Please copy the URL above and open it manually.")
    
    print("3. Waiting for authorization callback...")
    print("   This may take a few minutes...")
    
    # Wait for authorization code
    timeout = 300  # 5 minutes timeout
    start_time = time.time()
    
    while auth_code is None and server_running and (time.time() - start_time) < timeout:
        time.sleep(1)
    
    if auth_code is None:
        print("❌ Authorization timed out or was cancelled.")
        return
    
    print(f"✅ Authorization successful! Code received: {auth_code[:10]}...")
    
    # Exchange code for token
    token_data = exchange_code_for_token(auth_code)
    if not token_data:
        print("❌ Failed to exchange authorization code for token.")
        return
    
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    expires_in = token_data.get('expires_in')
    
    if not access_token:
        print("❌ No access token received.")
        print(f"Response: {token_data}")
        return
    
    print("✅ Access token received successfully!")
    if expires_in:
        print(f"   Token expires in: {expires_in} seconds")
    
    # Test the token
    user_data = test_token(access_token)
    if user_data:
        user_info = user_data.get('resource', {})
        print(f"✅ Token is valid! Connected to Calendly user:")
        print(f"   Name: {user_info.get('name', 'Unknown')}")
        print(f"   Email: {user_info.get('email', 'Unknown')}")
        print(f"   URI: {user_info.get('uri', 'Unknown')}")
    else:
        print("⚠️  Token received but validation failed. It might still work.")
    
    # Update environment files
    print("4. Updating environment files...")
    if update_env_files(access_token, refresh_token):
        print("✅ Environment files updated successfully!")
    else:
        print("❌ Failed to update environment files.")
        print(f"   Please manually add: CALENDLY_ACCESS_TOKEN={access_token}")
    
    print()
    print("🎉 Calendly OAuth setup complete!")
    print()
    print("Next steps:")
    print("1. Your Calendly access token has been saved")
    print("2. Restart your MCP server to use the new token")
    print("3. Test Calendly functionality in your Flask app")
    
    if refresh_token:
        print(f"\n💡 Your refresh token: {refresh_token}")
        print("   Save this securely - it can generate new access tokens")

if __name__ == "__main__":
    main()
