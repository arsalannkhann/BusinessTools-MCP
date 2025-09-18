#!/usr/bin/env python3
"""
Flask Web App for Testing Sales MCP Server

This Flask application provides a web interface to test the Sales MCP Server
functionality through HTTP endpoints.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
import traceback

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Import the server module
from sales_mcp_server import SalesMCPServer
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("flask_app")

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all domains

# Global server instance
mcp_server = None

async def init_server():
    """Initialize the MCP server"""
    global mcp_server
    try:
        mcp_server = SalesMCPServer()
        await mcp_server.initialize()
        logger.info("MCP Server initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}")
        return False

def process_tool_parameters(tool_name: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Process and transform parameters based on tool requirements"""
    processed = parameters.copy()
    
    # Handle attendees parameter - convert comma-separated string to list
    if "attendees" in processed and isinstance(processed["attendees"], str):
        attendees_str = processed["attendees"].strip()
        if attendees_str:
            # Split by comma and clean up each email
            processed["attendees"] = [email.strip() for email in attendees_str.split(",") if email.strip()]
        else:
            del processed["attendees"]  # Remove empty attendees
    
    # Handle "to" parameter for Gmail - convert comma-separated string to list if multiple emails
    if "to" in processed and isinstance(processed["to"], str):
        to_str = processed["to"].strip()
        if to_str:
            # If multiple emails separated by comma, convert to list, otherwise keep as single string
            if "," in to_str:
                processed["to"] = [email.strip() for email in to_str.split(",") if email.strip()]
            # For single email, keep as string (Gmail tool handles both string and list)
        else:
            return {"error": "Recipient email address is required"}
    
    # Handle datetime parameters - ensure proper formatting
    datetime_fields = ["start_time", "end_time"]
    for field in datetime_fields:
        if field in processed and processed[field]:
            # HTML datetime-local format needs to be converted to ISO format
            datetime_value = processed[field]
            if "T" in datetime_value and not datetime_value.endswith("Z"):
                # Add timezone info if not present (assuming local timezone)
                processed[field] = datetime_value + ":00"  # Add seconds if missing
    
    # Handle numeric fields
    numeric_fields = ["duration_minutes", "max_results", "days_ahead"]
    for field in numeric_fields:
        if field in processed and processed[field]:
            try:
                processed[field] = int(processed[field])
            except ValueError:
                # Keep original value if conversion fails
                pass
    
    # Handle Google Sheets specific parameters
    if tool_name == "google_sheets":
        # Parse values parameter for write operations
        if "values" in processed and isinstance(processed["values"], str):
            try:
                import json
                processed["values"] = json.loads(processed["values"])
            except json.JSONDecodeError:
                # If JSON parsing fails, try to parse as simple CSV-like format
                values_str = processed["values"].strip()
                if values_str:
                    # Split by lines, then by commas
                    rows = []
                    for line in values_str.split('\n'):
                        if line.strip():
                            row = [cell.strip() for cell in line.split(',')]
                            rows.append(row)
                    processed["values"] = rows
    
    # Handle Google Drive specific parameters
    if tool_name == "google_drive":
        # Handle content parameter for file uploads
        if "content" in processed and processed["content"]:
            # Content is already a string, no processing needed for basic text files
            pass
        
        # Handle file sharing permissions
        if "role" in processed and not processed["role"]:
            processed["role"] = "reader"  # Default to reader if not specified
    
    # Handle Twilio specific parameters
    if tool_name == "twilio":
        # Handle recipients for bulk SMS - convert comma-separated string to list
        if "recipients" in processed and isinstance(processed["recipients"], str):
            recipients_str = processed["recipients"].strip()
            if recipients_str:
                processed["recipients"] = [phone.strip() for phone in recipients_str.split(",") if phone.strip()]
            else:
                del processed["recipients"]
        
        # Handle numeric fields for limits
        if "limit" in processed and processed["limit"]:
            try:
                processed["limit"] = int(processed["limit"])
            except ValueError:
                pass
        
        # Clean up phone number fields
        phone_fields = ["to", "from_number", "phone_number"]
        for field in phone_fields:
            if field in processed and processed[field]:
                phone_value = processed[field].strip()
                if phone_value:
                    processed[field] = phone_value
                else:
                    # Remove empty phone fields (except required ones)
                    if field != "to" and field != "phone_number":
                        del processed[field]
        
        # Clean up message content
        if "message" in processed and processed["message"]:
            processed["message"] = processed["message"].strip()
    
    return processed

@app.route('/')
def index():
    """Main page with server status and tool overview"""
    return render_template('index.html')

@app.route('/api/status')
def server_status():
    """Get server status"""
    try:
        if mcp_server is None:
            return jsonify({
                "status": "not_initialized",
                "message": "MCP Server not initialized"
            }), 500
        
        # Get tool registry status
        tools = mcp_server.tool_registry.list_mcp_tools() if mcp_server.tool_registry else []
        
        # Get auth status
        auth_status = mcp_server.google_auth.is_authenticated() if mcp_server.google_auth else False
        
        return jsonify({
            "status": "running",
            "tools_count": len(tools),
            "tools": [{"name": tool.name, "description": tool.description} for tool in tools],
            "google_auth": auth_status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/tools')
def list_tools():
    """List all available tools"""
    try:
        if mcp_server is None or mcp_server.tool_registry is None:
            return jsonify({"error": "MCP Server not initialized"}), 500
        
        tools = mcp_server.tool_registry.list_mcp_tools()
        tools_data = []
        
        for tool in tools:
            tool_info = {
                "name": tool.name,
                "description": tool.description,
                "configured": False,
                "error": None
            }
            
            # Check if tool is configured
            try:
                actual_tool = mcp_server.tool_registry.get_tool(tool.name)
                if actual_tool and hasattr(actual_tool, 'is_configured'):
                    tool_info["configured"] = actual_tool.is_configured()
            except Exception as e:
                tool_info["error"] = str(e)
            
            tools_data.append(tool_info)
        
        return jsonify({
            "tools": tools_data,
            "count": len(tools_data)
        })
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/status')
def auth_status():
    """Get Google authentication status"""
    try:
        if mcp_server is None or mcp_server.google_auth is None:
            return jsonify({
                "authenticated": False,
                "message": "Google Auth not configured"
            })
        
        is_auth = mcp_server.google_auth.is_authenticated()
        return jsonify({
            "authenticated": is_auth,
            "message": "Authenticated" if is_auth else "Not authenticated"
        })
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        return jsonify({
            "authenticated": False,
            "error": str(e)
        }), 500

@app.route('/api/test/tool/<tool_name>', methods=['POST'])
def test_tool(tool_name):
    """Test a specific tool with given parameters"""
    try:
        if mcp_server is None or mcp_server.tool_registry is None:
            return jsonify({"error": "MCP Server not initialized"}), 500
        
        tool = mcp_server.tool_registry.get_tool(tool_name)
        if not tool:
            return jsonify({"error": f"Tool '{tool_name}' not found"}), 404
        
        # Get parameters from request
        parameters = request.json or {}
        
        # Test the tool (this is a basic test - actual tool execution would need MCP protocol)
        result = {
            "tool": tool_name,
            "configured": tool.is_configured() if hasattr(tool, 'is_configured') else False,
            "parameters": parameters,
            "test_time": datetime.now().isoformat(),
            "status": "test_completed"
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing tool {tool_name}: {e}")
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/execute/tool/<tool_name>', methods=['POST'])
def execute_tool(tool_name):
    """Execute a specific tool with given parameters"""
    try:
        if mcp_server is None or mcp_server.tool_registry is None:
            return jsonify({"error": "MCP Server not initialized"}), 500
        
        tool = mcp_server.tool_registry.get_tool(tool_name)
        if not tool:
            return jsonify({"error": f"Tool '{tool_name}' not found"}), 404
        
        if not (hasattr(tool, 'is_configured') and tool.is_configured()):
            return jsonify({"error": f"Tool '{tool_name}' is not properly configured"}), 400
        
        # Get parameters from request
        data = request.json or {}
        action = data.get('action', '')
        parameters = data.get('parameters', {})
        
        if not action:
            return jsonify({"error": "Action parameter is required"}), 400
        
        # Process parameters based on tool and action
        processed_params = process_tool_parameters(tool_name, action, parameters)
        
        # Execute the tool
        async def run_tool():
            return await tool.execute(action, processed_params)
        
        # Run the async tool execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_tool())
        loop.close()
        
        # Format the response
        response = {
            "tool": tool_name,
            "action": action,
            "parameters": processed_params,
            "execution_time": datetime.now().isoformat(),
            "success": result.success,
            "result": result.data if result.success else None,
            "error": result.error if not result.success else None
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/tools/<tool_name>/actions')
def get_tool_actions(tool_name):
    """Get available actions for a specific tool"""
    try:
        # Define actions for each tool
        tool_actions = {
            "gmail": [
                {
                    "action": "send_email",
                    "name": "Send Email",
                    "description": "Send a plain text email",
                    "parameters": [
                        {"name": "to", "type": "email", "required": True, "description": "Recipient email address"},
                        {"name": "subject", "type": "text", "required": True, "description": "Email subject"},
                        {"name": "body", "type": "textarea", "required": True, "description": "Email body"},
                        {"name": "from_email", "type": "email", "required": False, "description": "Sender email (optional)"}
                    ]
                },
                {
                    "action": "send_html_email",
                    "name": "Send HTML Email",
                    "description": "Send an HTML formatted email",
                    "parameters": [
                        {"name": "to", "type": "email", "required": True, "description": "Recipient email address"},
                        {"name": "subject", "type": "text", "required": True, "description": "Email subject"},
                        {"name": "html_body", "type": "textarea", "required": True, "description": "HTML email body"},
                        {"name": "from_email", "type": "email", "required": False, "description": "Sender email (optional)"}
                    ]
                }
            ],
            "google_calendar": [
                {
                    "action": "create_event",
                    "name": "Create Event",
                    "description": "Create a new calendar event",
                    "parameters": [
                        {"name": "summary", "type": "text", "required": True, "description": "Event title/summary"},
                        {"name": "description", "type": "textarea", "required": False, "description": "Event description"},
                        {"name": "start_time", "type": "datetime-local", "required": True, "description": "Start time"},
                        {"name": "end_time", "type": "datetime-local", "required": True, "description": "End time"},
                        {"name": "attendees", "type": "text", "required": False, "description": "Attendee emails (comma-separated)"},
                        {"name": "location", "type": "text", "required": False, "description": "Event location"}
                    ]
                },
                {
                    "action": "list_events",
                    "name": "List Events",
                    "description": "List upcoming calendar events",
                    "parameters": [
                        {"name": "max_results", "type": "number", "required": False, "description": "Maximum number of events (default: 10)"},
                        {"name": "days_ahead", "type": "number", "required": False, "description": "Days to look ahead (default: 7)"}
                    ]
                }
            ],
            "google_meet": [
                {
                    "action": "create_meeting",
                    "name": "Create Meeting",
                    "description": "Create a Google Meet meeting",
                    "parameters": [
                        {"name": "title", "type": "text", "required": True, "description": "Meeting title"},
                        {"name": "start_time", "type": "datetime-local", "required": True, "description": "Start time"},
                        {"name": "duration_minutes", "type": "number", "required": True, "description": "Duration in minutes"},
                        {"name": "attendees", "type": "text", "required": False, "description": "Attendee emails (comma-separated)"},
                        {"name": "description", "type": "textarea", "required": False, "description": "Meeting description"}
                    ]
                }
            ],
            "calendly": [
                {
                    "action": "get_availability",
                    "name": "Get Availability",
                    "description": "Get available time slots",
                    "parameters": [
                        {"name": "event_type", "type": "text", "required": False, "description": "Event type"},
                        {"name": "start_date", "type": "date", "required": False, "description": "Start date"},
                        {"name": "end_date", "type": "date", "required": False, "description": "End date"}
                    ]
                }
            ],
            "google_drive": [
                {
                    "action": "list_files",
                    "name": "List Files",
                    "description": "List files and folders in Google Drive",
                    "parameters": [
                        {"name": "folder_id", "type": "text", "required": False, "description": "Folder ID to list (root if empty)"},
                        {"name": "query", "type": "text", "required": False, "description": "Search query"},
                        {"name": "max_results", "type": "number", "required": False, "description": "Maximum results (default: 10)"}
                    ]
                },
                {
                    "action": "upload_file",
                    "name": "Upload File",
                    "description": "Upload a new file to Google Drive",
                    "parameters": [
                        {"name": "name", "type": "text", "required": True, "description": "File name"},
                        {"name": "content", "type": "textarea", "required": True, "description": "File content"},
                        {"name": "parent_folder_id", "type": "text", "required": False, "description": "Parent folder ID"},
                        {"name": "mime_type", "type": "text", "required": False, "description": "MIME type (auto-detected if empty)"}
                    ]
                },
                {
                    "action": "create_folder",
                    "name": "Create Folder",
                    "description": "Create a new folder in Google Drive",
                    "parameters": [
                        {"name": "name", "type": "text", "required": True, "description": "Folder name"},
                        {"name": "parent_folder_id", "type": "text", "required": False, "description": "Parent folder ID"}
                    ]
                },
                {
                    "action": "share_file",
                    "name": "Share File",
                    "description": "Share a file with others",
                    "parameters": [
                        {"name": "file_id", "type": "text", "required": True, "description": "File ID to share"},
                        {"name": "email", "type": "email", "required": True, "description": "Email to share with"},
                        {"name": "role", "type": "select", "options": ["reader", "writer", "commenter"], "required": False, "description": "Permission role"}
                    ]
                }
            ],
            "google_sheets": [
                {
                    "action": "create_spreadsheet",
                    "name": "Create Spreadsheet",
                    "description": "Create a new Google Sheets spreadsheet",
                    "parameters": [
                        {"name": "title", "type": "text", "required": True, "description": "Spreadsheet title"}
                    ]
                },
                {
                    "action": "read_range",
                    "name": "Read Range",
                    "description": "Read data from a spreadsheet range",
                    "parameters": [
                        {"name": "spreadsheet_id", "type": "text", "required": True, "description": "Spreadsheet ID"},
                        {"name": "range", "type": "text", "required": True, "description": "Range (e.g., 'Sheet1!A1:C10')"}
                    ]
                },
                {
                    "action": "write_range",
                    "name": "Write Range",
                    "description": "Write data to a spreadsheet range",
                    "parameters": [
                        {"name": "spreadsheet_id", "type": "text", "required": True, "description": "Spreadsheet ID"},
                        {"name": "range", "type": "text", "required": True, "description": "Range (e.g., 'Sheet1!A1:C10')"},
                        {"name": "values", "type": "textarea", "required": True, "description": "Values as JSON array (e.g., [['A1', 'B1'], ['A2', 'B2']])"}
                    ]
                },
                {
                    "action": "add_sheet",
                    "name": "Add Sheet",
                    "description": "Add a new sheet to an existing spreadsheet",
                    "parameters": [
                        {"name": "spreadsheet_id", "type": "text", "required": True, "description": "Spreadsheet ID"},
                        {"name": "title", "type": "text", "required": True, "description": "Sheet title"}
                    ]
                },
                {
                    "action": "create_chart",
                    "name": "Create Chart",
                    "description": "Create a chart in the spreadsheet",
                    "parameters": [
                        {"name": "spreadsheet_id", "type": "text", "required": True, "description": "Spreadsheet ID"},
                        {"name": "sheet_name", "type": "text", "required": True, "description": "Sheet name"},
                        {"name": "chart_type", "type": "select", "options": ["BAR", "LINE", "PIE", "COLUMN"], "required": True, "description": "Chart type"},
                        {"name": "data_range", "type": "text", "required": True, "description": "Data range (e.g., 'A1:B10')"}
                    ]
                }
            ],
            "twilio": [
                {
                    "action": "send_sms",
                    "name": "Send SMS",
                    "description": "Send SMS message to a phone number",
                    "parameters": [
                        {"name": "to", "type": "tel", "required": True, "description": "Recipient phone number (e.g., +1234567890 or 1234567890)", "placeholder": "+1234567890"},
                        {"name": "message", "type": "textarea", "required": True, "description": "SMS message content", "placeholder": "Hello! This is a test message."},
                        {"name": "from_number", "type": "tel", "required": False, "description": "Sender phone number (optional, uses configured number if empty)", "placeholder": "+1234567890"},
                        {"name": "media_url", "type": "url", "required": False, "description": "Media URL for MMS (optional)", "placeholder": "https://example.com/image.jpg"}
                    ]
                },
                {
                    "action": "send_whatsapp",
                    "name": "Send WhatsApp",
                    "description": "Send WhatsApp message",
                    "parameters": [
                        {"name": "to", "type": "tel", "required": True, "description": "Recipient WhatsApp number", "placeholder": "+1234567890"},
                        {"name": "message", "type": "textarea", "required": True, "description": "WhatsApp message content", "placeholder": "Hello from WhatsApp!"},
                        {"name": "media_url", "type": "url", "required": False, "description": "Media URL for attachment (optional)", "placeholder": "https://example.com/image.jpg"}
                    ]
                },
                {
                    "action": "make_call",
                    "name": "Make Call",
                    "description": "Make a voice call",
                    "parameters": [
                        {"name": "to", "type": "tel", "required": True, "description": "Recipient phone number", "placeholder": "+1234567890"},
                        {"name": "from_number", "type": "tel", "required": False, "description": "Caller phone number (optional)", "placeholder": "+1234567890"},
                        {"name": "twiml_url", "type": "url", "required": False, "description": "TwiML URL for call instructions (optional)", "placeholder": "http://demo.twilio.com/docs/voice.xml"}
                    ]
                },
                {
                    "action": "send_bulk_sms",
                    "name": "Send Bulk SMS",
                    "description": "Send SMS to multiple recipients",
                    "parameters": [
                        {"name": "recipients", "type": "text", "required": True, "description": "Phone numbers (comma-separated)", "placeholder": "+1234567890, +1987654321, +1555123456"},
                        {"name": "message", "type": "textarea", "required": True, "description": "SMS message content", "placeholder": "Hello everyone! This is a bulk message."},
                        {"name": "from_number", "type": "tel", "required": False, "description": "Sender phone number (optional)", "placeholder": "+1234567890"}
                    ]
                },
                {
                    "action": "get_message_history",
                    "name": "Message History",
                    "description": "Get SMS message history",
                    "parameters": [
                        {"name": "limit", "type": "number", "required": False, "description": "Number of messages to retrieve (default: 20)", "placeholder": "20"},
                        {"name": "to", "type": "tel", "required": False, "description": "Filter by recipient number", "placeholder": "+1234567890"},
                        {"name": "from_number", "type": "tel", "required": False, "description": "Filter by sender number", "placeholder": "+1234567890"}
                    ]
                },
                {
                    "action": "get_call_history",
                    "name": "Call History",
                    "description": "Get call history and logs",
                    "parameters": [
                        {"name": "limit", "type": "number", "required": False, "description": "Number of calls to retrieve (default: 20)", "placeholder": "20"},
                        {"name": "to", "type": "tel", "required": False, "description": "Filter by recipient number", "placeholder": "+1234567890"},
                        {"name": "from_number", "type": "tel", "required": False, "description": "Filter by caller number", "placeholder": "+1234567890"}
                    ]
                },
                {
                    "action": "check_phone_number",
                    "name": "Check Phone Number",
                    "description": "Validate phone number and get carrier info",
                    "parameters": [
                        {"name": "phone_number", "type": "tel", "required": True, "description": "Phone number to validate", "placeholder": "+1234567890"}
                    ]
                },
                {
                    "action": "get_account_usage",
                    "name": "Account Usage",
                    "description": "Get Twilio account usage and balance",
                    "parameters": []
                }
            ],
            "stripe": [
                {
                    "action": "create_customer",
                    "name": "Create Customer",
                    "description": "Create a new Stripe customer",
                    "parameters": [
                        {"name": "email", "type": "email", "required": True, "description": "Customer email address"},
                        {"name": "name", "type": "text", "required": False, "description": "Customer full name"},
                        {"name": "phone", "type": "tel", "required": False, "description": "Customer phone number"},
                        {"name": "description", "type": "textarea", "required": False, "description": "Customer description"}
                    ]
                },
                {
                    "action": "list_customers",
                    "name": "List Customers",
                    "description": "List all Stripe customers",
                    "parameters": [
                        {"name": "limit", "type": "number", "required": False, "description": "Number of customers to retrieve (default: 10)"}
                    ]
                },
                {
                    "action": "get_customer",
                    "name": "Get Customer",
                    "description": "Get details of a specific customer",
                    "parameters": [
                        {"name": "customer_id", "type": "text", "required": True, "description": "Stripe customer ID"}
                    ]
                },
                {
                    "action": "create_payment_intent",
                    "name": "Create Payment Intent",
                    "description": "Create a payment intent for processing payments",
                    "parameters": [
                        {"name": "amount", "type": "number", "required": True, "description": "Amount in cents (e.g., 2000 for $20.00)"},
                        {"name": "currency", "type": "text", "required": True, "description": "Currency code (e.g., 'usd', 'eur')"},
                        {"name": "customer", "type": "text", "required": False, "description": "Customer ID"},
                        {"name": "description", "type": "textarea", "required": False, "description": "Payment description"}
                    ]
                },
                {
                    "action": "list_payment_intents",
                    "name": "List Payment Intents",
                    "description": "List payment intents",
                    "parameters": [
                        {"name": "limit", "type": "number", "required": False, "description": "Number of payment intents to retrieve (default: 10)"},
                        {"name": "customer", "type": "text", "required": False, "description": "Filter by customer ID"}
                    ]
                },
                {
                    "action": "create_product",
                    "name": "Create Product",
                    "description": "Create a new product in Stripe",
                    "parameters": [
                        {"name": "name", "type": "text", "required": True, "description": "Product name"},
                        {"name": "description", "type": "textarea", "required": False, "description": "Product description"}
                    ]
                },
                {
                    "action": "create_price",
                    "name": "Create Price",
                    "description": "Create a price for a product",
                    "parameters": [
                        {"name": "product", "type": "text", "required": True, "description": "Product ID"},
                        {"name": "unit_amount", "type": "number", "required": True, "description": "Price in cents"},
                        {"name": "currency", "type": "text", "required": True, "description": "Currency code"}
                    ]
                },
                {
                    "action": "create_subscription",
                    "name": "Create Subscription",
                    "description": "Create a subscription for a customer",
                    "parameters": [
                        {"name": "customer", "type": "text", "required": True, "description": "Customer ID"},
                        {"name": "price_id", "type": "text", "required": True, "description": "Price ID for the subscription"}
                    ]
                }
            ]
        }
        
        if tool_name not in tool_actions:
            return jsonify({"error": f"No actions defined for tool '{tool_name}'"}), 404
        
        return jsonify({
            "tool": tool_name,
            "actions": tool_actions[tool_name]
        })
    except Exception as e:
        logger.error(f"Error getting actions for tool {tool_name}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/run-tests')
def run_all_tests():
    """Run comprehensive server tests"""
    try:
        async def run_tests():
            results = {
                "server_init": False,
                "google_auth": False,
                "tools": {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Test server initialization
            try:
                if mcp_server is not None:
                    results["server_init"] = True
            except Exception as e:
                logger.error(f"Server init test failed: {e}")
            
            # Test Google auth
            try:
                if mcp_server and mcp_server.google_auth:
                    results["google_auth"] = mcp_server.google_auth.is_authenticated()
            except Exception as e:
                logger.error(f"Google auth test failed: {e}")
            
            # Test individual tools
            try:
                if mcp_server and mcp_server.tool_registry:
                    tools = mcp_server.tool_registry.list_mcp_tools()
                    for tool in tools:
                        try:
                            actual_tool = mcp_server.tool_registry.get_tool(tool.name)
                            if actual_tool and hasattr(actual_tool, 'is_configured'):
                                results["tools"][tool.name] = actual_tool.is_configured()
                            else:
                                results["tools"][tool.name] = False
                        except Exception as e:
                            results["tools"][tool.name] = f"Error: {str(e)}"
            except Exception as e:
                logger.error(f"Tools test failed: {e}")
            
            return results
        
        # Run the async tests
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        test_results = loop.run_until_complete(run_tests())
        loop.close()
        
        return jsonify(test_results)
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

def create_app():
    """Application factory"""
    return app

if __name__ == '__main__':
    # Initialize the MCP server
    async def startup():
        success = await init_server()
        if not success:
            logger.error("Failed to initialize MCP server. Flask app will still run but with limited functionality.")
        
        # Start Flask app
        logger.info("Starting Flask web app on http://127.0.0.1:5000")
        app.run(debug=True, host='127.0.0.1', port=5000)
    
    # Run the startup
    asyncio.run(startup())

