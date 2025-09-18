"""
Gmail/SMTP integration tool
Handles email sending and management
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
import mcp.types as types
from typing import Dict, Any, Optional, List
from .base import SalesTool, ToolResult, validate_required_params

class GmailTool(SalesTool):
    """Gmail/SMTP operations"""
    
    def __init__(self):
        super().__init__("gmail", "Gmail/SMTP integration for email sending")
        self.google_auth = None
        self.gmail_service = None
        self.smtp_email = None
        self.smtp_password = None
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Gmail connection"""
        # Try Google OAuth first
        if google_auth and google_auth.is_authenticated():
            try:
                self.google_auth = google_auth
                self.gmail_service = google_auth.get_service('gmail')
                
                # Test Gmail API connection
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.executor,
                    lambda: self.gmail_service.users().getProfile(userId='me').execute()
                )
                
                self.logger.info("Gmail API connection validated")
                return True
                
            except Exception as e:
                self.logger.warning(f"Gmail API initialization failed: {e}")
        
        # Fallback to SMTP
        self.smtp_email = settings.gmail_email
        self.smtp_password = settings.gmail_app_password
        
        if self.smtp_email and self.smtp_password:
            # Test SMTP connection
            try:
                await self._test_smtp_connection()
                self.logger.info("Gmail SMTP connection validated")
                return True
            except Exception as e:
                self.logger.error(f"Gmail SMTP initialization failed: {e}")
                return False
        
        self.logger.warning("No Gmail credentials configured")
        return False
    
    async def _test_smtp_connection(self):
        """Test SMTP connection"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._test_smtp_sync)
    
    def _test_smtp_sync(self):
        """Synchronous SMTP connection test"""
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(self.smtp_email, self.smtp_password)
    
    async def execute(self, action: str, params: Dict[str, Any]) -> ToolResult:
        """Execute Gmail operations"""
        try:
            if action == "send_email":
                return await self._send_email(params)
            elif action == "send_html_email":
                return await self._send_html_email(params)
            elif action == "get_profile":
                return await self._get_profile(params)
            elif action == "list_messages":
                return await self._list_messages(params)
            elif action == "get_message":
                return await self._get_message(params)
            elif action == "search_messages":
                return await self._search_messages(params)
            else:
                return self._create_error_result(f"Unknown action: {action}")
        
        except Exception as e:
            return self._create_error_result(f"Gmail operation failed: {str(e)}")
    
    async def _send_email(self, params: Dict[str, Any]) -> ToolResult:
        """Send plain text email"""
        error = validate_required_params(params, ["to", "subject", "body"])
        if error:
            return self._create_error_result(error)
        
        to_emails = params["to"] if isinstance(params["to"], list) else [params["to"]]
        subject = params["subject"]
        body = params["body"]
        from_email = params.get("from", self.smtp_email)
        cc_emails = params.get("cc", [])
        bcc_emails = params.get("bcc", [])
        
        if self.gmail_service:
            return await self._send_via_api(to_emails, subject, body, from_email, cc_emails, bcc_emails)
        else:
            return await self._send_via_smtp(to_emails, subject, body, from_email, cc_emails, bcc_emails)
    
    async def _send_html_email(self, params: Dict[str, Any]) -> ToolResult:
        """Send HTML email"""
        error = validate_required_params(params, ["to", "subject"])
        if error:
            return self._create_error_result(error)
        
        if not params.get("html_body") and not params.get("body"):
            return self._create_error_result("Either html_body or body is required")
        
        to_emails = params["to"] if isinstance(params["to"], list) else [params["to"]]
        subject = params["subject"]
        html_body = params.get("html_body", "")
        text_body = params.get("body", "")
        from_email = params.get("from", self.smtp_email)
        cc_emails = params.get("cc", [])
        bcc_emails = params.get("bcc", [])
        
        if self.gmail_service:
            return await self._send_html_via_api(to_emails, subject, html_body, text_body, from_email, cc_emails, bcc_emails)
        else:
            return await self._send_html_via_smtp(to_emails, subject, html_body, text_body, from_email, cc_emails, bcc_emails)
    
    async def _send_via_api(self, to_emails, subject, body, from_email, cc_emails, bcc_emails):
        """Send email via Gmail API"""
        message = MIMEText(body)
        message['to'] = ', '.join(to_emails)
        message['subject'] = subject
        if from_email:
            message['from'] = from_email
        if cc_emails:
            message['cc'] = ', '.join(cc_emails)
        
        # Add BCC recipients to the message but not to headers
        all_recipients = to_emails + cc_emails + bcc_emails
        
        loop = asyncio.get_event_loop()
        
        try:
            raw_message = await loop.run_in_executor(
                self.executor,
                lambda: base64.urlsafe_b64encode(message.as_bytes()).decode()
            )
            
            send_result = await loop.run_in_executor(
                self.executor,
                lambda: self.gmail_service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()
            )
            
            return self._create_success_result({
                'message_id': send_result['id'],
                'sent': True,
                'recipients': all_recipients,
                'method': 'gmail_api'
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to send email via API: {str(e)}")
    
    async def _send_via_smtp(self, to_emails, subject, body, from_email, cc_emails, bcc_emails):
        """Send email via SMTP"""
        message = MIMEText(body)
        message['From'] = from_email or self.smtp_email
        message['To'] = ', '.join(to_emails)
        message['Subject'] = subject
        if cc_emails:
            message['Cc'] = ', '.join(cc_emails)
        
        all_recipients = to_emails + cc_emails + bcc_emails
        
        loop = asyncio.get_event_loop()
        
        try:
            await loop.run_in_executor(
                self.executor,
                lambda: self._send_smtp_sync(message, all_recipients)
            )
            
            return self._create_success_result({
                'sent': True,
                'recipients': all_recipients,
                'method': 'smtp'
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to send email via SMTP: {str(e)}")
    
    def _send_smtp_sync(self, message, recipients):
        """Synchronous SMTP sending"""
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(self.smtp_email, self.smtp_password)
            server.send_message(message, to_addrs=recipients)
    
    async def _send_html_via_api(self, to_emails, subject, html_body, text_body, from_email, cc_emails, bcc_emails):
        """Send HTML email via Gmail API"""
        message = MIMEMultipart('alternative')
        message['to'] = ', '.join(to_emails)
        message['subject'] = subject
        if from_email:
            message['from'] = from_email
        if cc_emails:
            message['cc'] = ', '.join(cc_emails)
        
        if text_body:
            text_part = MIMEText(text_body, 'plain')
            message.attach(text_part)
        
        if html_body:
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)
        
        all_recipients = to_emails + cc_emails + bcc_emails
        loop = asyncio.get_event_loop()
        
        try:
            raw_message = await loop.run_in_executor(
                self.executor,
                lambda: base64.urlsafe_b64encode(message.as_bytes()).decode()
            )
            
            send_result = await loop.run_in_executor(
                self.executor,
                lambda: self.gmail_service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()
            )
            
            return self._create_success_result({
                'message_id': send_result['id'],
                'sent': True,
                'recipients': all_recipients,
                'method': 'gmail_api'
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to send HTML email via API: {str(e)}")
    
    async def _send_html_via_smtp(self, to_emails, subject, html_body, text_body, from_email, cc_emails, bcc_emails):
        """Send HTML email via SMTP"""
        message = MIMEMultipart('alternative')
        message['From'] = from_email or self.smtp_email
        message['To'] = ', '.join(to_emails)
        message['Subject'] = subject
        if cc_emails:
            message['Cc'] = ', '.join(cc_emails)
        
        if text_body:
            text_part = MIMEText(text_body, 'plain')
            message.attach(text_part)
        
        if html_body:
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)
        
        all_recipients = to_emails + cc_emails + bcc_emails
        loop = asyncio.get_event_loop()
        
        try:
            await loop.run_in_executor(
                self.executor,
                lambda: self._send_smtp_sync(message, all_recipients)
            )
            
            return self._create_success_result({
                'sent': True,
                'recipients': all_recipients,
                'method': 'smtp'
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to send HTML email via SMTP: {str(e)}")
    
    async def _get_profile(self, params: Dict[str, Any]) -> ToolResult:
        """Get Gmail profile (API only)"""
        if not self.gmail_service:
            return self._create_error_result("Gmail API not available, only SMTP is configured")
        
        loop = asyncio.get_event_loop()
        
        try:
            profile = await loop.run_in_executor(
                self.executor,
                lambda: self.gmail_service.users().getProfile(userId='me').execute()
            )
            
            return self._create_success_result({
                'email_address': profile.get('emailAddress', ''),
                'messages_total': profile.get('messagesTotal', 0),
                'threads_total': profile.get('threadsTotal', 0),
                'history_id': profile.get('historyId', '')
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get profile: {str(e)}")
    
    async def _list_messages(self, params: Dict[str, Any]) -> ToolResult:
        """List messages (API only)"""
        if not self.gmail_service:
            return self._create_error_result("Gmail API not available, only SMTP is configured")
        
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        label_ids = params.get("label_ids", [])
        include_spam_trash = params.get("include_spam_trash", False)
        
        query_params = {
            'userId': 'me',
            'maxResults': max_results,
            'includeSpamTrash': include_spam_trash
        }
        
        if query:
            query_params['q'] = query
        if label_ids:
            query_params['labelIds'] = label_ids
        
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.gmail_service.users().messages().list(**query_params).execute()
            )
            
            messages = result.get('messages', [])
            
            return self._create_success_result({
                'messages': messages,
                'result_size_estimate': result.get('resultSizeEstimate', 0),
                'next_page_token': result.get('nextPageToken')
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to list messages: {str(e)}")
    
    async def _get_message(self, params: Dict[str, Any]) -> ToolResult:
        """Get message details (API only)"""
        if not self.gmail_service:
            return self._create_error_result("Gmail API not available, only SMTP is configured")
        
        error = validate_required_params(params, ["message_id"])
        if error:
            return self._create_error_result(error)
        
        message_id = params["message_id"]
        format_type = params.get("format", "full")  # full, metadata, minimal, raw
        
        loop = asyncio.get_event_loop()
        
        try:
            message = await loop.run_in_executor(
                self.executor,
                lambda: self.gmail_service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format=format_type
                ).execute()
            )
            
            return self._create_success_result(message)
            
        except Exception as e:
            return self._create_error_result(f"Failed to get message: {str(e)}")
    
    async def _search_messages(self, params: Dict[str, Any]) -> ToolResult:
        """Search messages (API only)"""
        if not self.gmail_service:
            return self._create_error_result("Gmail API not available, only SMTP is configured")
        
        error = validate_required_params(params, ["query"])
        if error:
            return self._create_error_result(error)
        
        query = params["query"]
        max_results = params.get("max_results", 10)
        
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.gmail_service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=max_results
                ).execute()
            )
            
            messages = result.get('messages', [])
            
            # Get detailed info for each message
            detailed_messages = []
            for message in messages[:5]:  # Limit to first 5 for performance
                try:
                    detailed = await loop.run_in_executor(
                        self.executor,
                        lambda msg_id=message['id']: self.gmail_service.users().messages().get(
                            userId='me',
                            id=msg_id,
                            format='metadata'
                        ).execute()
                    )
                    detailed_messages.append(detailed)
                except Exception:
                    detailed_messages.append(message)
            
            return self._create_success_result({
                'messages': detailed_messages,
                'total_found': result.get('resultSizeEstimate', 0),
                'query': query
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to search messages: {str(e)}")
    
    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition"""
        return types.Tool(
            name="gmail",
            description="Gmail/SMTP email operations for sending and managing emails",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "send_email", "send_html_email", "get_profile", 
                            "list_messages", "get_message", "search_messages"
                        ],
                        "description": "The action to perform"
                    },
                    "to": {"type": ["string", "array"], "description": "Recipient email(s)"},
                    "cc": {"type": "array", "items": {"type": "string"}, "description": "CC recipients"},
                    "bcc": {"type": "array", "items": {"type": "string"}, "description": "BCC recipients"},
                    "from": {"type": "string", "description": "Sender email"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body (plain text)"},
                    "html_body": {"type": "string", "description": "Email body (HTML)"},
                    "message_id": {"type": "string", "description": "Gmail message ID"},
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 10},
                    "format": {"type": "string", "enum": ["full", "metadata", "minimal", "raw"], "description": "Message format", "default": "full"},
                    "label_ids": {"type": "array", "items": {"type": "string"}, "description": "Label IDs to filter by"},
                    "include_spam_trash": {"type": "boolean", "description": "Include messages in spam and trash", "default": False}
                },
                "required": ["action"]
            }
        )
    
    async def cleanup(self):
        """Clean up resources"""
        if self.executor:
            self.executor.shutdown(wait=False)
        self.logger.info("Gmail tool cleaned up")
