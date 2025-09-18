#!/bin/bash

# Simple script to start the Sales MCP Server

echo "🚀 Starting Sales MCP Server..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if not already installed
if [ ! -f "venv/.installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Check for configuration files
if [ ! -f ".env" ] && [ ! -f "settings.json" ]; then
    echo "⚠️  Warning: No configuration files found (.env or settings.json)"
    echo "   Please copy .env.example to .env and configure your API keys"
    echo "   Or copy settings.example.json to settings.json and configure there"
fi

# Start the server
echo "Starting MCP Server..."
python3 sales_mcp_server.py