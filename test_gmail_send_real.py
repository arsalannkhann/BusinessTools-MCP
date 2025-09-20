#!/usr/bin/env python3
"""
Gmail Send Email Test Script - Send to your actual email
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from sales_mcp_server import SalesMCPServer

async def test_gmail_send_to_real_email():
    """Test sending an email via Gmail to your actual email"""
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
            
        # Get user profile to get their email address
        logger.info("Getting user profile to determine email address...")
        profile_result = await gmail_tool.execute('get_profile', {})
        
        if not profile_result.success:
            logger.error(f"Failed to get profile: {profile_result.error}")
            return
            
        # Debug: Show full profile result
        logger.info(f"Profile result: {profile_result.data}")
        
        # Try to get the actual email address
        user_email = profile_result.data.get('email_address') or profile_result.data.get('emailAddress')
        
        if not user_email or user_email == 'test@example.com':
            # If we can't get the real email, let's use a manual one
            # Let's check if we can get it from Google Auth directly
            logger.warning("Could not get real email from profile, checking Google Auth...")
            
            if hasattr(gmail_tool, 'google_auth') and gmail_tool.google_auth:
                try:
                    # Try to get user info from Google Auth
                    gmail_service = gmail_tool.google_auth.get_service("gmail")
                    loop = asyncio.get_event_loop()
                    raw_profile = await loop.run_in_executor(
                        None,
                        lambda: gmail_service.users().getProfile(userId="me").execute()
                    )
                    logger.info(f"Raw Gmail profile: {raw_profile}")
                    user_email = raw_profile.get('emailAddress', user_email)
                except Exception as e:
                    logger.warning(f"Could not get email from raw profile: {e}")
        
        if not user_email or user_email == 'test@example.com':
            # Fallback: ask user to provide email or use a test one
            logger.warning("Using fallback email. Please check your Gmail credentials.")
            user_email = "test@example.com"  # You can change this to your actual email
        
        logger.info(f"Target email address: {user_email}")
        
        # Send a test email
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        email_params = {
            'to': user_email,
            'subject': f'🎉 Test Email from Sales MCP Server - {timestamp}',
            'body': f"""
Hello!

This is a test email sent from the Sales MCP Server at {timestamp}.

🎉 GREAT NEWS: The Gmail integration is working perfectly! 

Key details:
✅ Server: Sales MCP Server initialized successfully
✅ Tool: Gmail API connected and authenticated  
✅ Time: {timestamp}
✅ Status: All systems operational
✅ Email sending: FUNCTIONAL

Your Sales MCP Server is ready to handle:
• Automated email campaigns
• Customer communications  
• Lead follow-ups
• Meeting notifications
• And much more!

Best regards,
Your Sales MCP Server 🤖

P.S. This email confirms that your Gmail tool is working correctly for automated sales workflows.
""",
            'body_type': 'plain'
        }
        
        logger.info(f"📧 Sending test email to: {user_email}")
        logger.info(f"📋 Subject: {email_params['subject']}")
        
        # Send the email
        result = await gmail_tool.execute('send_email', email_params)
        
        if result.success:
            logger.info("🎉 EMAIL SENT SUCCESSFULLY!")
            if hasattr(result.data, 'get') and result.data.get('id'):
                logger.info(f"📧 Message ID: {result.data.get('id')}")
                logger.info(f"🧵 Thread ID: {result.data.get('threadId', 'N/A')}")
            logger.info(f"📬 Check your inbox at: {user_email}")
            logger.info("✅ Gmail tool is fully functional for your sales workflows!")
        else:
            logger.error(f"❌ EMAIL SENDING FAILED: {result.error}")
            
    except Exception as e:
        logger.error(f"Error during email test: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main function"""
    logger.info("=== Gmail Send Email Test (To Real Email) ===")
    await test_gmail_send_to_real_email()
    logger.info("=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
