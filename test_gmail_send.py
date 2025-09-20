#!/usr/bin/env python3
"""
Gmail Send Email Test Script
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from sales_mcp_server import SalesMCPServer

async def test_gmail_send():
    """Test sending an email via Gmail"""
    try:
        # Initialize MCP Server
        logger.info("Initializing MCP Server...")
        server = SalesMCPServer()
        await server.initialize()
        
        # Get Gmail tool
        if 'gmail' not in server.tool_registry.tools:
            logger.error("Gmail tool not found!")
            return
            
        gmail_tool = server.tool_registry.tools['gmail']
        
        if not getattr(gmail_tool, '_configured', False):
            logger.error("Gmail tool is not configured!")
            return
            
        # First get user profile to get their email address
        logger.info("Getting user profile to determine email address...")
        profile_result = await gmail_tool.execute('get_profile', {})
        
        if not profile_result.success:
            logger.error(f"Failed to get profile: {profile_result.error}")
            return
            
        user_email = profile_result.data.get('emailAddress', 'test@example.com')
        logger.info(f"User email: {user_email}")
        
        # Send a test email
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        email_params = {
            'to': user_email,  # Send to yourself
            'subject': f'Test Email from Sales MCP Server - {timestamp}',
            'body': f"""
Hello!

This is a test email sent from the Sales MCP Server at {timestamp}.

The Gmail integration is working correctly! 🎉

Key details:
- Server: Sales MCP Server
- Tool: Gmail API
- Time: {timestamp}
- Status: All systems operational

Best regards,
Your Sales MCP Server
""",
            'body_type': 'plain'
        }
        
        logger.info(f"Sending test email to: {user_email}")
        logger.info(f"Subject: {email_params['subject']}")
        
        # Send the email
        result = await gmail_tool.execute('send_email', email_params)
        
        if result.success:
            logger.info("✅ EMAIL SENT SUCCESSFULLY!")
            logger.info(f"Message ID: {result.data.get('id', 'N/A')}")
            logger.info(f"Thread ID: {result.data.get('threadId', 'N/A')}")
            logger.info(f"Check your inbox at: {user_email}")
        else:
            logger.error(f"❌ EMAIL SENDING FAILED: {result.error}")
            
    except Exception as e:
        logger.error(f"Error during email test: {e}")

async def main():
    """Main function"""
    logger.info("=== Gmail Send Email Test ===")
    await test_gmail_send()
    logger.info("=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
