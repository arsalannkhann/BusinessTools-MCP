#!/bin/bash
# Quick setup script for AWS deployment with Gemini TTS

set -e

echo "🚀 Setting up MCP Server with Gemini TTS Interface for AWS Deployment"
echo "=" * 80

# Check Python version
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
required_version="3.11"

if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
    echo "❌ Python 3.11 or higher required. Found: $python_version"
    exit 1
fi
echo "✅ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Update pip
echo "📈 Updating pip..."
pip install --upgrade pip

# Install base requirements
echo "📦 Installing base requirements..."
pip install -r requirements.txt

# Install TTS requirements
echo "🎤 Installing TTS requirements..."
pip install -r requirements.tts.txt

# Install additional development tools
echo "🛠️  Installing development tools..."
pip install numpy  # For audio generation in tests

echo "✅ All dependencies installed successfully!"

# Check AWS CLI
echo "☁️  Checking AWS CLI..."
if command -v aws &> /dev/null; then
    echo "✅ AWS CLI found: $(aws --version)"
else
    echo "❌ AWS CLI not found. Please install it:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
fi

# Check Docker
echo "🐳 Checking Docker..."
if command -v docker &> /dev/null; then
    echo "✅ Docker found: $(docker --version)"
else
    echo "❌ Docker not found. Please install Docker Desktop:"
    echo "   https://www.docker.com/products/docker-desktop"
fi

echo ""
echo "🎉 Setup complete! Next steps:"
echo ""
echo "1. Set up your API keys:"
echo "   export GEMINI_API_KEY='your-gemini-api-key'"
echo "   export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account.json'"
echo ""
echo "2. Test locally:"
echo "   ./test_local.py"
echo ""
echo "3. Configure AWS deployment:"
echo "   vim aws/deploy.sh  # Update DOMAIN_NAME, CERTIFICATE_ARN, etc."
echo ""
echo "4. Deploy to AWS:"
echo "   ./aws/deploy.sh"
echo ""
echo "🚀 Ready for deployment!"
