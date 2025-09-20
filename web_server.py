"""
Flask Web Server for Sales MCP Server
Provides a web interface to interact with the MCP server tools
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from config.settings import Settings
from sales_mcp_server import SalesMCPServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize MCP server
settings = Settings()
mcp_server = SalesMCPServer()

# Store the initialization status
initialization_status = {
    'initialized': False,
    'tools': {},
    'error': None,
    'timestamp': None
}

async def initialize_server():
    """Initialize the MCP server asynchronously"""
    global initialization_status
    try:
        await mcp_server.initialize()
        
        # Get tool status
        tool_status = {}
        for tool_name, tool in mcp_server.tool_registry.tools.items():
            tool_status[tool_name] = {
                'configured': tool.is_configured() if hasattr(tool, 'is_configured') else True,
                'description': tool.description if hasattr(tool, 'description') else 'No description available'
            }
        
        initialization_status.update({
            'initialized': True,
            'tools': tool_status,
            'error': None,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info("MCP Server initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}")
        initialization_status.update({
            'initialized': False,
            'tools': {},
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

# Initialize server on startup
def init_server():
    """Initialize server in a new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(initialize_server())
    finally:
        loop.close()

@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get server and tools status"""
    return jsonify(initialization_status)

@app.route('/api/tools')
def get_tools():
    """Get available tools and their configurations"""
    if not initialization_status['initialized']:
        return jsonify({'error': 'Server not initialized'}), 500
    
    tools_info = {}
    for tool_name, tool in mcp_server.tool_registry.tools.items():
        tools_info[tool_name] = {
            'name': tool_name,
            'description': getattr(tool, 'description', 'No description available'),
            'configured': tool.is_configured() if hasattr(tool, 'is_configured') else True,
            'actions': getattr(tool, 'get_available_actions', lambda: [])()
        }
    
    return jsonify(tools_info)

@app.route('/api/tool/<tool_name>/execute', methods=['POST'])
def execute_tool(tool_name):
    """Execute a tool action"""
    if not initialization_status['initialized']:
        return jsonify({'error': 'Server not initialized'}), 500
    
    if tool_name not in mcp_server.tool_registry.tools:
        return jsonify({'error': f'Tool {tool_name} not found'}), 404
    
    try:
        data = request.get_json()
        action = data.get('action')
        params = data.get('params', {})
        
        if not action:
            return jsonify({'error': 'Action is required'}), 400
        
        # Execute the tool action asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            tool = mcp_server.tool_registry.tools[tool_name]
            result = loop.run_until_complete(tool.execute(action, params))
            
            # Convert result to dict if it's a ToolResult object
            if hasattr(result, 'success'):
                result_dict = {
                    'success': result.success,
                    'data': result.data,
                    'error': result.error,
                    'metadata': getattr(result, 'metadata', {})
                }
            else:
                result_dict = {'success': True, 'data': result}
            
            return jsonify(result_dict)
            
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/tool/<tool_name>/actions')
def get_tool_actions(tool_name):
    """Get available actions for a specific tool"""
    if not initialization_status['initialized']:
        return jsonify({'error': 'Server not initialized'}), 500
    
    if tool_name not in mcp_server.tool_registry.tools:
        return jsonify({'error': f'Tool {tool_name} not found'}), 404
    
    tool = mcp_server.tool_registry.tools[tool_name]
    
    # Define actions for each tool
    actions_map = {
        'google_search': [
            {
                'name': 'search',
                'description': 'Perform a web search',
                'parameters': [
                    {'name': 'query', 'type': 'string', 'required': True, 'description': 'Search query'},
                    {'name': 'num_results', 'type': 'number', 'required': False, 'description': 'Number of results (default: 10)'}
                ]
            },
            {
                'name': 'search_images',
                'description': 'Search for images',
                'parameters': [
                    {'name': 'query', 'type': 'string', 'required': True, 'description': 'Image search query'},
                    {'name': 'num_results', 'type': 'number', 'required': False, 'description': 'Number of results (default: 10)'}
                ]
            }
        ],
        'hubspot': [
            {
                'name': 'get_contacts',
                'description': 'Get HubSpot contacts',
                'parameters': [
                    {'name': 'limit', 'type': 'number', 'required': False, 'description': 'Number of contacts to retrieve'}
                ]
            }
        ],
        'twilio': [
            {
                'name': 'send_sms',
                'description': 'Send SMS message',
                'parameters': [
                    {'name': 'to', 'type': 'string', 'required': True, 'description': 'Phone number'},
                    {'name': 'message', 'type': 'string', 'required': True, 'description': 'Message content'}
                ]
            }
        ]
    }
    
    return jsonify(actions_map.get(tool_name, []))

@app.route('/api/test')
def test_api():
    """Test API endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'server_initialized': initialization_status['initialized']
    })

@app.route('/api/auth/status')
def get_auth_status():
    """Get authentication status"""
    if not initialization_status['initialized']:
        return jsonify({'error': 'Server not initialized'}), 500
    
    # Check if Google Auth is available
    google_auth_status = {
        'available': mcp_server.google_auth is not None,
        'authenticated': False,
        'services': []
    }
    
    if mcp_server.google_auth:
        google_auth_status['authenticated'] = True
        google_auth_status['services'] = ['Gmail', 'Calendar', 'Drive', 'Sheets', 'Meet']
    
    return jsonify({
        'google': google_auth_status,
        'overall_status': 'authenticated' if google_auth_status['authenticated'] else 'not_authenticated'
    })

@app.route('/api/run-tests')
def run_tests():
    """Run comprehensive system tests"""
    if not initialization_status['initialized']:
        return jsonify({'error': 'Server not initialized'}), 500
    
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': 'passed',
        'tests': []
    }
    
    # Test each tool
    for tool_name, tool in mcp_server.tool_registry.tools.items():
        test_result = {
            'name': f'{tool_name}_configuration',
            'description': f'Check {tool_name} tool configuration',
            'status': 'passed' if (hasattr(tool, 'is_configured') and tool.is_configured()) else 'warning',
            'details': f'{tool_name} is configured and ready' if (hasattr(tool, 'is_configured') and tool.is_configured()) else f'{tool_name} has limited functionality'
        }
        test_results['tests'].append(test_result)
    
    # Check if any tests failed
    failed_tests = [t for t in test_results['tests'] if t['status'] == 'failed']
    warning_tests = [t for t in test_results['tests'] if t['status'] == 'warning']
    
    if failed_tests:
        test_results['overall_status'] = 'failed'
    elif warning_tests:
        test_results['overall_status'] = 'warning'
    
    return jsonify(test_results)

if __name__ == '__main__':
    # Initialize the server
    init_server()
    
    # Start Flask app on port 8080 to avoid conflicts with AirPlay
    port = 8080
    logger.info(f"Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
