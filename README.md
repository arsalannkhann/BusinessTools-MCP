# Theta-MCP: AI-Powered Sales Assistant

A comprehensive sales automation platform combining Model Context Protocol (MCP) server with Gemini AI voice interface, featuring 13+ integrated sales tools and AWS deployment capabilities.

## 🚀 Features

### Core Capabilities
- **Voice Interface**: Gemini AI-powered speech-to-text and text-to-speech
- **MCP Server**: Model Context Protocol server with extensive tool integration
- **Real-time Processing**: WebSocket-based voice communication
- **AWS Deployment**: Production-ready with ECS Fargate and auto-scaling

### Integrated Sales Tools
- **CRM**: HubSpot, Salesforce integration
- **Communication**: Gmail, Google Meet, Twilio SMS
- **Lead Generation**: LinkedIn Sales Navigator, Apollo
- **Data Management**: Google Sheets, Google Drive
- **Payments**: Stripe integration
- **Scheduling**: Calendly automation
- **Search**: Google Search API

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Voice Client  │◄──►│  Gemini AI TTS   │◄──►│   MCP Server    │
│   (WebSocket)   │    │    Interface     │    │  (13+ Tools)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🛠️ Quick Start

### Local Development
```bash
# Clone repository
git clone <repository-url>
cd Theta-MCP

# Setup environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure settings
cp config/settings.example.json config/settings.json
# Add your API keys to config/settings.json

# Run locally
python ./deployment/test_local.py
```

### Production Deployment
```bash
# Setup AWS deployment
./deployment/setup_aws.sh

# Deploy to AWS ECS
./deployment/aws/deploy.sh
```

## 📁 Project Structure

```
Theta-MCP/
├── sales_mcp_server.py          # Main MCP server
├── gemini_tts_interface.py      # Voice interface with Gemini AI
├── health_check.py              # Health monitoring
├── refresh_google_token.py      # Token management
├── config/                      # Configuration files
│   ├── google_auth.py          # Google authentication
│   ├── settings.py             # Settings loader
│   └── settings.example.json   # Configuration template
├── tools/                       # Sales automation tools
│   ├── hubspot_tool.py         # HubSpot CRM integration
│   ├── salesforce_tool.py      # Salesforce integration
│   ├── gmail_tool.py           # Gmail automation
│   ├── linkedin_tool.py        # LinkedIn Sales Navigator
│   ├── apollo_tool.py          # Lead generation
│   ├── stripe_tool.py          # Payment processing
│   ├── calendly_tool.py        # Scheduling automation
│   └── ... (13+ tools total)
├── deployment/                  # Deployment configurations
│   ├── aws/                    # AWS-specific files
│   ├── docker/                 # Docker configurations
│   ├── setup_aws.sh           # AWS setup script
│   └── test_local.py          # Local testing
└── tests/                      # Test suite
```

## 🔧 Configuration

### Required API Keys
- Google Cloud (Speech-to-Text, Text-to-Speech, Calendar, Gmail)
- Gemini AI API key
- HubSpot, Salesforce, LinkedIn, Apollo (as needed)
- AWS credentials (for deployment)

### Environment Variables
Copy `.env.example` to `.env` and configure:
```
GOOGLE_CLOUD_PROJECT=your-project
GEMINI_API_KEY=your-gemini-key
HUBSPOT_API_KEY=your-hubspot-key
# ... additional API keys
```

## 🚀 AWS Deployment

### Infrastructure
- **ECS Fargate**: Serverless container orchestration
- **Application Load Balancer**: Traffic distribution
- **Auto Scaling**: 2-10 instances based on demand
- **EFS Storage**: Persistent token and log storage
- **Secrets Manager**: Secure API key management
- **CloudWatch**: Monitoring and logging

### Deployment Process
1. Configure AWS credentials
2. Run `./deployment/setup_aws.sh`
3. Execute `./deployment/aws/deploy.sh`
4. Access via provided ALB endpoint

## 🧪 Testing

```bash
# Run test suite
python -m pytest tests/

# Test local deployment
python ./deployment/test_local.py

# Health check
curl http://localhost:8000/health
```

## 📚 API Documentation

### MCP Server Endpoints
- `GET /health` - Health check
- `POST /tools/{tool_name}` - Execute tool
- `WebSocket /voice` - Voice interface

### Voice Interface
- Real-time speech-to-text processing
- Gemini AI conversation handling
- Text-to-speech response generation
- WebSocket-based communication

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Create an issue in this repository
- Check the deployment guide: `./deployment/README.md`
- Review test configurations: `./tests/README.md`

---

**Built with ❤️ using Python, FastAPI, Gemini AI, and AWS**
