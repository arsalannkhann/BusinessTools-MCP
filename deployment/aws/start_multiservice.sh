#!/bin/bash
# Multi-service startup script for AWS deployment
# Runs both MCP Server and Gemini TTS Interface

set -e

echo "🚀 Starting Multi-Service MCP Server with Gemini TTS Interface..."

# Check if running in production environment
if [ "$ENVIRONMENT" != "production" ]; then
    echo "⚠️  Warning: ENVIRONMENT not set to 'production'"
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p credentials tokens logs backups

# Initialize Google credentials from AWS Secrets Manager
setup_google_credentials() {
    echo "🔑 Setting up Google credentials from AWS Secrets Manager..."
    
    if [ -n "$GOOGLE_CREDENTIALS_JSON" ]; then
        echo "$GOOGLE_CREDENTIALS_JSON" > credentials/google_credentials.json
        echo "✅ Google credentials written to file"
    else
        echo "❌ GOOGLE_CREDENTIALS_JSON environment variable not set"
        return 1
    fi
}

# Check for existing token or create from credentials
setup_google_token() {
    echo "🔐 Setting up Google token..."
    
    if [ ! -f "tokens/google_token.json" ]; then
        if [ -f "token.json" ]; then
            echo "📋 Moving existing token to tokens directory..."
            cp token.json tokens/google_token.json
        else
            echo "❌ No Google token found. You may need to run OAuth flow manually."
            echo "   Token will be created automatically on first API call if refresh token exists."
        fi
    fi
}

# Start MCP Server in background
start_mcp_server() {
    echo "🔧 Starting MCP Server on port 8000..."
    python sales_mcp_server.py &
    MCP_PID=$!
    echo "✅ MCP Server started with PID: $MCP_PID"
}

# Start Gemini TTS Interface in background
start_tts_interface() {
    echo "🎤 Starting Gemini TTS Interface on port 8001..."
    python gemini_tts_interface.py &
    TTS_PID=$!
    echo "✅ TTS Interface started with PID: $TTS_PID"
}

# Health monitoring function
health_monitor() {
    echo "🏥 Starting health monitor..."
    while true; do
        sleep 60
        
        # Check MCP Server health
        if ! kill -0 $MCP_PID 2>/dev/null; then
            echo "❌ MCP Server died, restarting..."
            start_mcp_server
        fi
        
        # Check TTS Interface health
        if ! kill -0 $TTS_PID 2>/dev/null; then
            echo "❌ TTS Interface died, restarting..."
            start_tts_interface
        fi
        
        # Check if services are responding
        if ! curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            echo "⚠️  MCP Server health check failed"
        fi
        
        if ! curl -sf http://localhost:8001/health > /dev/null 2>&1; then
            echo "⚠️  TTS Interface health check failed"
        fi
    done
}

# Cleanup function
cleanup() {
    echo "🧹 Shutting down services..."
    kill $MCP_PID $TTS_PID 2>/dev/null || true
    wait $MCP_PID $TTS_PID 2>/dev/null || true
    echo "✅ Services shut down cleanly"
}

# Trap signals for graceful shutdown
trap cleanup SIGTERM SIGINT

# Main startup sequence
main() {
    # Setup credentials and tokens
    setup_google_credentials || {
        echo "❌ Failed to setup Google credentials"
        exit 1
    }
    
    setup_google_token
    
    # Wait for AWS services to be ready
    echo "⏳ Waiting for AWS services to be ready..."
    sleep 10
    
    # Start services
    start_mcp_server
    sleep 5
    start_tts_interface
    sleep 5
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to be ready..."
    timeout=60
    counter=0
    
    while [ $counter -lt $timeout ]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1 && \
           curl -sf http://localhost:8001/health > /dev/null 2>&1; then
            echo "✅ Both services are healthy and ready!"
            break
        fi
        
        sleep 2
        counter=$((counter + 2))
    done
    
    if [ $counter -ge $timeout ]; then
        echo "❌ Services failed to become ready within $timeout seconds"
        cleanup
        exit 1
    fi
    
    echo "🎉 Multi-service deployment successful!"
    echo "🔧 MCP Server: http://localhost:8000"
    echo "🎤 TTS Interface: http://localhost:8001"
    echo "📊 Auto-refresh enabled for Google tokens"
    
    # Start health monitoring and wait
    health_monitor
}

# Run main function
main
