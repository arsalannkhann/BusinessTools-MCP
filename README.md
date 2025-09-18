# 🚀 Sales MCP Server - Complete Sales Automation Platform

A comprehensive Model Context Protocol (MCP) server providing essential sales tools for automated sales workflows, CRM integration, communication, and AI-powered tool selection with **Theta AI integration**.

## ⚡ Key Highlights

- **🤖 AI-Powered Tool Selection** - Theta AI analyzes queries and recommends the best tools automatically
- **🔄 Auto-Refreshing OAuth Tokens** - Advanced Calendly helper with automatic token management
- **💳 Complete Payment Processing** - Full Stripe integration with 25+ operations
- **📱 9 Production-Ready Tools** - Enterprise-grade integrations across all sales functions
- **🔧 MCP Compatible** - All tools use proper MCP schema definitions

## 🛠️ Supported Tools (9/9 Configured)

### 💰 Payment Processing
- **✅ Stripe** - Complete payment ecosystem (customers, subscriptions, invoices, products, refunds)

### 📅 Scheduling & Meetings  
- **✅ Calendly** - Event scheduling with auto-refresh token management
- **✅ Google Calendar** - Calendar events and availability checking
- **✅ Google Meet** - Video meeting creation and management

### 💬 Communication
- **✅ Gmail** - Email sending and management
- **✅ Twilio** - SMS and WhatsApp messaging

### 📊 CRM & Sales Management
- **✅ HubSpot** - Contacts, deals, companies management  
- **✅ Salesforce** - Leads, opportunities, accounts management

### 📁 Document Management
- **✅ Google Sheets** - Spreadsheet operations and data management
- **✅ Google Drive** - File storage and sharing

## � Quick Start

### Prerequisites
- Python 3.9+
- API keys for desired services
- Google OAuth credentials (for Google services)

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure Python environment (if needed)
python -c "from config.settings import Settings; print('Environment ready!')"
```

### 2. Configuration

Copy the environment template and configure your services:

```bash
cp env.template .env
# Edit .env with your API keys and credentials
```

### 3. Quick Test

```bash
# Test all tools and Theta AI integration
python sales_mcp_server.py

# Or run the MCP server directly
python -m mcp_server
```

## 🔧 Configuration Guide

### Essential Environment Variables

```bash
# === Core Configuration ===
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_TOKEN_PATH=token.json

# === AI Integration ===
THETA_API_KEY=your_theta_api_key_here

# === Payment Processing ===
STRIPE_API_KEY=sk_test_your_stripe_secret_key_here

# === Scheduling (Auto-Refresh Enabled) ===
CALENDLY_ACCESS_TOKEN=your_calendly_access_token
CALENDLY_CLIENT_ID=your_oauth_client_id        # For auto-refresh
CALENDLY_CLIENT_SECRET=your_oauth_secret        # For auto-refresh  
CALENDLY_REFRESH_TOKEN=your_refresh_token       # For auto-refresh

# === Communication ===
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# === CRM Integration ===
HUBSPOT_API_KEY=your_hubspot_api_key
SALESFORCE_CLIENT_ID=your_sf_client_id
SALESFORCE_CLIENT_SECRET=your_sf_client_secret
SALESFORCE_USERNAME=your_sf_username
SALESFORCE_PASSWORD=your_sf_password
SALESFORCE_SECURITY_TOKEN=your_sf_security_token
```

### 🤖 Theta AI Integration

The server includes intelligent tool selection powered by Theta AI:

```python
# Automatic tool recommendation based on user query
query = "I want to schedule a meeting with a potential customer"
# Theta AI recommends: Calendly

query = "Send pricing information to john@example.com" 
# Theta AI recommends: Gmail

query = "Create an invoice for $500"
# Theta AI recommends: Stripe
```

## 💳 Stripe Payment Processing (25+ Operations)

### Customer Management
- `create_customer`, `get_customer`, `update_customer`, `list_customers`

### Payment Processing  
- `create_payment_intent`, `get_payment_intent`, `confirm_payment_intent`
- `refund_payment`, `list_charges`

### Subscription Management
- `create_subscription`, `get_subscription`, `update_subscription`
- `cancel_subscription`, `list_subscriptions`

### Product & Pricing
- `create_product`, `get_product`, `list_products`
- `create_price`, `get_price`, `list_prices`

### Invoice Management
- `create_invoice`, `get_invoice`, `send_invoice`, `list_invoices`

### Account Management
- `get_balance`

**Configuration:**
```bash
STRIPE_API_KEY=sk_test_your_secret_key_here  # From https://dashboard.stripe.com/apikeys
```

## 📅 Enhanced Calendly Integration

### 🔄 Auto-Refresh Token Management

The Calendly tool includes advanced OAuth token management:

- **Automatic token validation** before every API call
- **Background token refresh** every 55 minutes  
- **Automatic .env file updates** with new tokens
- **Graceful error handling** and fallback support

### Setup Options

**Option 1: Personal Access Token (Simple)**
```bash
CALENDLY_ACCESS_TOKEN=your_personal_token_here
```

**Option 2: OAuth with Auto-Refresh (Recommended)**
```bash
CALENDLY_CLIENT_ID=your_oauth_app_client_id
CALENDLY_CLIENT_SECRET=your_oauth_app_client_secret
CALENDLY_ACCESS_TOKEN=your_initial_access_token  
CALENDLY_REFRESH_TOKEN=your_refresh_token
```

### Available Operations
- `get_user`, `list_event_types`, `get_event_type`
- `list_scheduled_events`, `get_scheduled_event`, `cancel_scheduled_event`
- `list_invitees`, `get_invitee`
- `create_webhook`, `list_webhooks`, `delete_webhook`

## 🏢 CRM Integration

### HubSpot
```bash
HUBSPOT_API_KEY=your_hubspot_api_key  # From HubSpot Settings > Integrations > API key
```
**Operations:** `create_contact`, `get_contact`, `update_contact`, `search_contacts`, `create_deal`, `get_deal`, `update_deal`, `search_deals`

### Salesforce  
```bash
SALESFORCE_CLIENT_ID=your_connected_app_client_id
SALESFORCE_CLIENT_SECRET=your_connected_app_secret
SALESFORCE_USERNAME=your_sf_username
SALESFORCE_PASSWORD=your_sf_password
SALESFORCE_SECURITY_TOKEN=your_sf_security_token
```

## 📱 Communication Tools

### Gmail Integration
Uses Google OAuth - no additional configuration needed beyond Google credentials.

**Operations:** `send_email`, `send_html_email`, `get_profile`, `list_messages`, `get_message`, `search_messages`

### Twilio (SMS/WhatsApp)
```bash
TWILIO_ACCOUNT_SID=your_account_sid      # From Twilio Console
TWILIO_AUTH_TOKEN=your_auth_token        # From Twilio Console  
TWILIO_PHONE_NUMBER=your_twilio_number   # Your Twilio phone number
```

**Operations:** `send_sms`, `send_whatsapp`, `make_call`, `get_message_history`, `get_call_history`

## 📊 Google Workspace Integration

### Setup Google OAuth

1. **Create Google Cloud Project**
   - Go to https://console.cloud.google.com/
   - Create new project or select existing
   - Enable required APIs: Gmail, Calendar, Drive, Sheets, Meet

2. **Create OAuth Credentials** 
   - Go to APIs & Services > Credentials
   - Create OAuth 2.0 Client ID (Desktop application)
   - Download credentials as `credentials.json`

3. **First-time Authentication**
   ```bash
   python -c "from config.google_auth import GoogleAuthManager; import asyncio; asyncio.run(GoogleAuthManager().initialize())"
   ```

### Available Google Services
- **Google Calendar** - Event management and availability  
- **Google Meet** - Video meeting creation
- **Gmail** - Email operations
- **Google Drive** - File management and sharing
- **Google Sheets** - Spreadsheet operations

## 🚀 Deployment Options

### Local Development
```bash
# Run the MCP server
python sales_mcp_server.py

# Or start with specific configuration
python -c "import asyncio; from sales_mcp_server import main; asyncio.run(main())"
```

### Docker Deployment
```bash
# Build and run
docker build -t sales-mcp-server .
docker run -d -p 8000:8000 --env-file .env sales-mcp-server
```

### Production Setup
```bash
# Use the provided start script
chmod +x start.sh
./start.sh

# Or with systemd (see deploy/systemd/)
sudo cp deploy/systemd/sales-mcp-server.service /etc/systemd/system/
sudo systemctl enable sales-mcp-server
sudo systemctl start sales-mcp-server
```

## 🧪 Testing & Validation

### Verify Installation
```bash
# Test all tools and connections
python -c "
import asyncio
from config.settings import Settings
from tools.base import SalesToolRegistry

async def test_tools():
    settings = Settings()
    registry = SalesToolRegistry()
    await registry.initialize_tools(settings)
    print(f'✅ Successfully initialized {len(registry.tools)} tools')
    
    # Test Theta AI
    try:
        from orionac_ai.client import Theta
        client = Theta(api_key='c26113ee4346db73')
        response = client.generate('Test connection', stream=False)
        print('✅ Theta AI connection working')
    except Exception as e:
        print(f'❌ Theta AI: {e}')

asyncio.run(test_tools())
"
```

### Individual Tool Testing
```bash
# Test specific tools
python -c "
import asyncio
from tools.calendly_tool import CalendlyTool
from config.settings import Settings

async def test_calendly():
    tool = CalendlyTool()
    settings = Settings()
    success = await tool.initialize(settings)
    print(f'Calendly: {'✅' if success else '❌'}')
    
asyncio.run(test_calendly())
"
```

## 🔧 Troubleshooting

### Common Issues

**1. "Module not found" errors**
```bash
# Ensure you're in the correct virtual environment
source .venv/bin/activate  # or venv/bin/activate
pip install -r requirements.txt
```

**2. Google OAuth issues**
```bash
# Delete existing token and re-authenticate
rm token.json
python -c "from config.google_auth import GoogleAuthManager; import asyncio; asyncio.run(GoogleAuthManager().initialize())"
```

**3. Calendly token issues**
```bash
# Check token validity
python -c "
import asyncio
from tools.calendly_helper import CalendlyTokenManager

async def check_token():
    manager = CalendlyTokenManager()
    manager.load_credentials()
    is_valid = await manager.validate_token()
    print(f'Token valid: {is_valid}')
    
asyncio.run(check_token())
"
```

**4. Stripe configuration issues**
```bash
# Verify Stripe key format
echo $STRIPE_API_KEY  # Should start with sk_test_ or sk_live_
```

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
python sales_mcp_server.py
```

## 📚 API Reference

### MCP Tool Structure
Each tool follows the MCP protocol:
```python
{
    "name": "tool_name",
    "description": "Tool description",
    "inputSchema": {
        "type": "object", 
        "properties": {
            "action": {"type": "string", "enum": ["action1", "action2"]},
            "param1": {"type": "string", "description": "Parameter description"}
        }
    }
}
```

### Example Tool Usage
```json
{
    "tool": "stripe",
    "action": "create_customer",
    "name": "John Doe",
    "email": "john@example.com",
    "metadata": {"source": "website"}
}
```

## 🎯 Use Cases

### Sales Workflow Automation
1. **Lead Qualification** → HubSpot contact creation
2. **Meeting Scheduling** → Calendly integration with auto-refresh
3. **Follow-up Communication** → Gmail + Twilio messaging
4. **Payment Processing** → Stripe invoicing and subscriptions
5. **Document Management** → Google Drive file sharing

### Example AI-Powered Workflow
```
User: "I need to schedule a demo with john@company.com and send him pricing"

Theta AI Analysis:
1. Recommends Calendly for scheduling
2. Suggests Gmail for sending pricing information  
3. Proposes Stripe for creating pricing estimates
```

## 🔄 Auto-Refresh Features

### Calendly Token Management
- ✅ **Automatic token validation** before each request
- ✅ **55-minute refresh cycle** in background  
- ✅ **Environment file updates** with new tokens
- ✅ **Graceful fallback** to manual refresh if needed

### Google Services
- ✅ **Automatic credential refresh** using refresh tokens
- ✅ **Multi-service authentication** with single OAuth flow

## 📄 File Structure

```
MCP/
├── sales_mcp_server.py          # Main server entry point
├── requirements.txt             # Python dependencies
├── .env                         # Environment configuration
├── Dockerfile                   # Container deployment
├── config/
│   ├── settings.py             # Configuration management
│   └── google_auth.py          # Google OAuth handler
├── tools/
│   ├── base.py                 # Tool registry and base classes
│   ├── stripe_tool.py          # Payment processing (25+ ops)
│   ├── calendly_tool.py        # Scheduling with auto-refresh
│   ├── calendly_helper.py      # Advanced OAuth management
│   ├── gmail_tool.py           # Email management
│   ├── hubspot_tool.py         # CRM integration
│   └── [other_tools].py        # Additional integrations
└── deploy/
    ├── systemd/                # Linux service configuration
    └── nginx/                  # Reverse proxy setup
```

## 🚀 Next Steps

### Extending the Server
1. **Add New Tools** - Follow the base tool pattern in `tools/base.py`
2. **Custom Integrations** - Implement your own MCP tool definitions
3. **Enhanced AI** - Customize Theta AI recommendations for your workflow

### Production Considerations
- **Security** - Use environment variables for all secrets
- **Monitoring** - Implement logging and health checks
- **Scaling** - Consider load balancing for high-volume usage
- **Backup** - Regular backup of tokens and configuration

---

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Verify all environment variables are set correctly
3. Test individual tools before running the full server
4. Enable debug logging for detailed error information

**Status: 9/9 Tools Configured and Ready for Production** ✅
```

## 🔧 Tool Configuration

### Google Services Setup
1. Create project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable APIs: Calendar, Drive, Sheets, Gmail
3. Create OAuth 2.0 credentials
4. Download `credentials.json`
5. Run authentication flow

### CRM Integration
- **HubSpot**: Get access token from [HubSpot Developer](https://developers.hubspot.com/)
- **Salesforce**: Use username, password, and security token
- **Pipedrive**: Get API token from Pipedrive settings

### Communication Tools
- **Slack**: Create bot app, get bot token or webhook URL
- **Zoom**: Create JWT app, get API key/secret

## 📊 Usage Examples

### Basic Tool Usage
```python
# Example: Create HubSpot contact and schedule meeting
import asyncio
from tools.hubspot_tool import HubSpotTool
from tools.google_calendar_tool import GoogleCalendarTool

async def sales_workflow():
    # Initialize tools
    hubspot = HubSpotTool()
    calendar = GoogleCalendarTool()
    
    # Create contact
    contact_result = await hubspot.execute("create_contact", {
        "properties": {
            "firstname": "John",
            "lastname": "Doe", 
            "email": "john.doe@example.com",
            "company": "Acme Corp"
        }
    })
    
    # Schedule meeting
    if contact_result.success:
        meeting_result = await calendar.execute("create_event", {
            "summary": "Sales Meeting",
            "start": "2024-02-01T10:00:00Z",
            "end": "2024-02-01T11:00:00Z",
            "attendees": ["john.doe@example.com"]
        })
    
    return contact_result, meeting_result

# Run workflow
results = asyncio.run(sales_workflow())
```

### MCP Integration
```python
# Example: Using with MCP client
import mcp.client as mcp_client

async def mcp_example():
    client = mcp_client.Client("sales-mcp-server")
    
    # List available tools
    tools = await client.list_tools()
    print(f"Available tools: {[tool.name for tool in tools]}")
    
    # Execute tool
    result = await client.call_tool("hubspot", {
        "action": "create_contact",
        "properties": {
            "email": "prospect@company.com",
            "firstname": "Jane",
            "lastname": "Prospect"
        }
    })
    
    return result
```

## 🔄 Workflow Examples

### Complete Lead-to-Close Workflow
1. **Lead Generation**: Apollo.io search → HubSpot contact creation
2. **Outreach**: Outreach.io sequence → Gmail follow-up 
3. **Scheduling**: Calendly booking → Google Calendar event
4. **Documentation**: Google Sheets tracking → Google Drive files
5. **Communication**: Slack notifications → Zoom meetings

## 🚀 Deployment Options

### 1. Local Development
- Direct Python execution
- SQLite for development data
- File-based logging

### 2. Docker Container
- Containerized deployment
- Environment-based configuration
- Health checks included

### 3. Production (EC2 + SystemD)
- SystemD service management
- Nginx reverse proxy
- SSL termination
- Log rotation

## 🔒 Security

### Authentication
- Google OAuth 2.0 for Google services
- API key authentication for third-party services
- Token-based authentication support

### Best Practices
- Environment variable configuration
- No hardcoded secrets
- TLS encryption in production
- Rate limiting enabled

## 🤝 Contributing

### Development Setup
```bash
# Install dev dependencies
pip install -r requirements.txt

# Setup pre-commit hooks
pre-commit install

# Run code formatting
black .
ruff check . --fix

# Type checking
mypy sales_mcp_server.py config/ tools/
```

### Adding New Tools
1. Create tool class in `tools/your_tool.py`
2. Inherit from `SalesTool` base class
3. Implement required methods
4. Add configuration to settings
5. Write tests
6. Update documentation

## ❓ Troubleshooting

### Common Issues

1. **Google Authentication Fails**
   - Verify `credentials.json` is present
   - Check enabled APIs in Google Console
   - Run authentication flow manually

2. **Tool Not Loading**
   - Check API keys in environment
   - Verify service configuration
   - Review tool-specific logs

3. **Connection Timeouts**
   - Increase timeout values
   - Check network connectivity
   - Verify service endpoints

### Debug Mode
```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG
python sales_mcp_server.py
```

## 📄 License

MIT License

## 🆘 Support


- Email: arsalankhan@orionac.in

---

*Built with ❤️ for sales teams worldwide*
