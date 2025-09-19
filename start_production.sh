#!/bin/bash
# Production deployment startup script
# Handles Google token refresh and server initialization

set -e  # Exit on any error

echo "🚀 Starting MCP Server Production Deployment..."

# Check if running in production environment
if [ "$ENVIRONMENT" != "production" ]; then
    echo "⚠️  Warning: ENVIRONMENT not set to 'production'"
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p credentials token_storage backups logs

# Check for credentials
if [ ! -f "credentials/google_credentials.json" ]; then
    echo "❌ Error: Google credentials not found at credentials/google_credentials.json"
    echo "   Please ensure your Google OAuth credentials are properly mounted"
    exit 1
fi

# Check if token needs refresh
echo "🔑 Checking Google token status..."
if [ -f "token_storage/google_token.json" ]; then
    python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('token_storage/google_token.json', 'r') as f:
        token = json.load(f)
    
    if 'expiry' in token:
        expiry = datetime.fromisoformat(token['expiry'].replace('Z', '+00:00'))
        now = datetime.now(expiry.tzinfo)
        hours_left = (expiry - now).total_seconds() / 3600
        
        print(f'Token expires in {hours_left:.1f} hours')
        
        if hours_left < 1:
            print('❌ Token expires soon, manual refresh may be needed')
            sys.exit(1)
        elif hours_left < 24:
            print('⚠️  Token expires within 24 hours')
        else:
            print('✅ Token is healthy')
    else:
        print('⚠️  Token format may be old, will auto-refresh')
        
except Exception as e:
    print(f'❌ Error checking token: {e}')
    sys.exit(1)
"
    
    TOKEN_CHECK_RESULT=$?
    if [ $TOKEN_CHECK_RESULT -eq 1 ]; then
        echo "🔄 Attempting token refresh..."
        python3 refresh_google_token.py || {
            echo "❌ Failed to refresh token automatically"
            echo "   Please run: python refresh_google_token.py"
            exit 1
        }
    fi
else
    echo "❌ No Google token found. Please authenticate first:"
    echo "   python calendly_oauth_complete.py"
    exit 1
fi

# Set environment variables for auto-refresh
export GOOGLE_CREDENTIALS_PATH="${GOOGLE_CREDENTIALS_PATH:-./credentials/google_credentials.json}"
export GOOGLE_TOKEN_PATH="${GOOGLE_TOKEN_PATH:-./token_storage/google_token.json}"
export GOOGLE_REFRESH_INTERVAL="${GOOGLE_REFRESH_INTERVAL:-1800}"  # 30 minutes
export GOOGLE_MIN_TOKEN_LIFETIME="${GOOGLE_MIN_TOKEN_LIFETIME:-300}"  # 5 minutes

# Start background token refresh (production mode)
echo "⚡ Enabling automatic token refresh..."
export ENVIRONMENT=production

# Health check before starting
echo "🏥 Running initial health check..."
python3 health_check.py || {
    echo "❌ Initial health check failed"
    exit 1
}

echo "✅ All checks passed. Starting MCP Server..."
echo "📊 Server will auto-refresh tokens every $GOOGLE_REFRESH_INTERVAL seconds"
echo "🔄 Tokens will refresh when < $GOOGLE_MIN_TOKEN_LIFETIME seconds remain"

# Start the MCP server
exec python3 sales_mcp_server.py
