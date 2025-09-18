"""
Twilio communication tool for SMS and voice capabilities
Provides comprehensive messaging and calling functionality for sales outreach
"""

import json
import logging
from typing import Dict, Any, Optional, List
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import mcp.types as types
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from .base import SalesTool, ToolResult

logger = logging.getLogger(__name__)

def validate_required_params(params: Dict[str, Any], required: List[str]) -> Optional[str]:
    """Validate required parameters"""
    missing = [param for param in required if param not in params or params[param] is None]
    if missing:
        return f"Missing required parameters: {', '.join(missing)}"
    return None

def format_phone_number(phone: str) -> str:
    """Format phone number to E.164 format"""
    if not phone or not phone.strip():
        raise ValueError("Phone number cannot be empty")
    
    phone = phone.strip()
    
    # If already in E.164 format, validate and return
    if phone.startswith('+'):
        digits_only = ''.join(filter(str.isdigit, phone))
        if len(digits_only) >= 10:
            return phone
        else:
            raise ValueError(f"Invalid phone number format: {phone}")
    
    # Remove all non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone))
    
    if not digits_only:
        raise ValueError(f"No digits found in phone number: {phone}")
    
    # Add country code if missing (assume US)
    if len(digits_only) == 10:
        return f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        return f"+{digits_only}"
    elif len(digits_only) >= 10:
        # For international numbers, add + if not present
        return f"+{digits_only}"
    else:
        raise ValueError(f"Phone number too short: {phone} (need at least 10 digits)")

class TwilioTool(SalesTool):
    """Twilio SMS and voice communication tool"""
    
    def __init__(self):
        super().__init__("twilio", "Twilio SMS and voice communication for sales outreach")
        self.client = None
        self.account_sid = None
        self.auth_token = None
        self.phone_number = None
        self.whatsapp_number = None
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Twilio tool"""
        try:
            self.account_sid = settings.twilio_account_sid
            self.auth_token = settings.twilio_auth_token
            self.phone_number = settings.twilio_phone_number
            self.whatsapp_number = getattr(settings, 'twilio_whatsapp_number', None)
            
            if not self.account_sid or not self.auth_token:
                self.logger.warning("Twilio credentials not configured")
                return False
            
            # Initialize Twilio client
            self.client = Client(self.account_sid, self.auth_token)
            
            # Test connection by fetching account info
            loop = asyncio.get_event_loop()
            account = await loop.run_in_executor(
                self.executor,
                lambda: self.client.api.accounts(self.account_sid).fetch()
            )
            
            self.logger.info(f"Twilio connection validated for account: {account.friendly_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Twilio tool: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return self.client is not None and self.account_sid is not None
    
    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition for Twilio"""
        return types.Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform",
                        "enum": [
                            "send_sms", "send_whatsapp", "make_call", "get_message_history",
                            "get_call_history", "send_bulk_sms", "schedule_message",
                            "check_phone_number", "get_account_usage", "get_available_numbers"
                        ]
                    },
                    "to": {
                        "type": "string",
                        "description": "Recipient phone number (E.164 format preferred)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message content for SMS/WhatsApp"
                    },
                    "from_number": {
                        "type": "string",
                        "description": "Sender phone number (optional, uses default if not specified)"
                    },
                    "media_url": {
                        "type": "string",
                        "description": "URL for media attachment (images, videos)"
                    }
                },
                "required": ["action"]
            }
        )
    
    async def execute(self, action: str, params: Dict[str, Any]) -> ToolResult:
        """Execute Twilio action"""
        if not self.client:
            return self._create_error_result("Twilio tool not initialized")
        
        try:
            # SMS Operations
            if action == "send_sms":
                return await self._send_sms(params)
            elif action == "send_whatsapp":
                return await self._send_whatsapp(params)
            elif action == "send_bulk_sms":
                return await self._send_bulk_sms(params)
            
            # Voice Operations
            elif action == "make_call":
                return await self._make_call(params)
            
            # History and Analytics
            elif action == "get_message_history":
                return await self._get_message_history(params)
            elif action == "get_call_history":
                return await self._get_call_history(params)
            elif action == "get_account_usage":
                return await self._get_account_usage(params)
            
            # Utility Operations
            elif action == "check_phone_number":
                return await self._check_phone_number(params)
            elif action == "get_available_numbers":
                return await self._get_available_numbers(params)
            elif action == "schedule_message":
                return await self._schedule_message(params)
            
            else:
                return self._create_error_result(f"Unknown action: {action}")
        
        except Exception as e:
            self.logger.error(f"Error executing Twilio action {action}: {e}")
            return self._create_error_result(f"Action failed: {str(e)}")
    
    async def _send_sms(self, params: Dict[str, Any]) -> ToolResult:
        """Send SMS message"""
        error = validate_required_params(params, ["to", "message"])
        if error:
            return self._create_error_result(error)
        
        try:
            # Validate and format phone numbers
            try:
                to_number = format_phone_number(params["to"])
            except ValueError as e:
                return self._create_error_result(f"Invalid recipient phone number: {str(e)}")
            
            from_number = params.get("from_number", self.phone_number)
            if not from_number:
                return self._create_error_result("No sender phone number configured")
            
            try:
                from_number = format_phone_number(from_number)
            except ValueError as e:
                return self._create_error_result(f"Invalid sender phone number: {str(e)}")
            
            message_body = params["message"]
            if not message_body or not message_body.strip():
                return self._create_error_result("Message body cannot be empty")
            
            media_url = params.get("media_url")
            
            message_data = {
                'body': message_body.strip(),
                'from_': from_number,
                'to': to_number
            }
            
            if media_url:
                message_data['media_url'] = [media_url]
            
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                self.executor,
                lambda: self.client.messages.create(**message_data)
            )
            
            return self._create_success_result({
                'message_sid': message.sid,
                'to': message.to,
                'from': message.from_,
                'body': message.body,
                'status': message.status,
                'date_created': message.date_created.isoformat() if message.date_created else None,
                'price': message.price,
                'direction': message.direction
            })
            
        except TwilioRestException as e:
            error_msg = f"Twilio SMS error (Code {e.code}): {e.msg}"
            if e.code == 21211:
                error_msg += " - Invalid phone number format. Use E.164 format (+1234567890)"
            elif e.code == 21408:
                error_msg += " - Phone number cannot receive SMS messages"
            elif e.code == 21219:
                error_msg += " - Sender phone number not configured correctly"
            return self._create_error_result(error_msg)
        except Exception as e:
            return self._create_error_result(f"Failed to send SMS: {str(e)}")
    
    async def _send_whatsapp(self, params: Dict[str, Any]) -> ToolResult:
        """Send WhatsApp message"""
        error = validate_required_params(params, ["to", "message"])
        if error:
            return self._create_error_result(error)
        
        if not self.whatsapp_number:
            return self._create_error_result("WhatsApp number not configured")
        
        try:
            to_number = f"whatsapp:{format_phone_number(params['to'])}"
            from_number = f"whatsapp:{self.whatsapp_number}"
            message_body = params["message"]
            media_url = params.get("media_url")
            
            message_data = {
                'body': message_body,
                'from_': from_number,
                'to': to_number
            }
            
            if media_url:
                message_data['media_url'] = [media_url]
            
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                self.executor,
                lambda: self.client.messages.create(**message_data)
            )
            
            return self._create_success_result({
                'message_sid': message.sid,
                'to': message.to,
                'from': message.from_,
                'body': message.body,
                'status': message.status,
                'date_created': message.date_created.isoformat() if message.date_created else None,
                'price': message.price
            })
            
        except TwilioRestException as e:
            return self._create_error_result(f"Twilio WhatsApp error: {e.msg}")
        except Exception as e:
            return self._create_error_result(f"Failed to send WhatsApp: {str(e)}")
    
    async def _make_call(self, params: Dict[str, Any]) -> ToolResult:
        """Make a voice call"""
        error = validate_required_params(params, ["to"])
        if error:
            return self._create_error_result(error)
        
        try:
            to_number = format_phone_number(params["to"])
            from_number = params.get("from_number", self.phone_number)
            
            # TwiML for the call - can be customized
            twiml_url = params.get("twiml_url", "http://demo.twilio.com/docs/voice.xml")
            
            loop = asyncio.get_event_loop()
            call = await loop.run_in_executor(
                self.executor,
                lambda: self.client.calls.create(
                    to=to_number,
                    from_=from_number,
                    url=twiml_url
                )
            )
            
            return self._create_success_result({
                'call_sid': call.sid,
                'to': call.to,
                'from': getattr(call, 'from_', getattr(call, 'from', from_number)),
                'status': call.status,
                'date_created': call.date_created.isoformat() if call.date_created else None,
                'duration': getattr(call, 'duration', None),
                'price': getattr(call, 'price', None)
            })
            
        except TwilioRestException as e:
            return self._create_error_result(f"Twilio call error: {e.msg}")
        except Exception as e:
            return self._create_error_result(f"Failed to make call: {str(e)}")
    
    async def _send_bulk_sms(self, params: Dict[str, Any]) -> ToolResult:
        """Send SMS to multiple recipients"""
        error = validate_required_params(params, ["recipients", "message"])
        if error:
            return self._create_error_result(error)
        
        try:
            recipients = params["recipients"]
            if isinstance(recipients, str):
                # Convert comma-separated string to list
                recipients = [r.strip() for r in recipients.split(",")]
            
            message_body = params["message"]
            from_number = params.get("from_number", self.phone_number)
            
            results = []
            loop = asyncio.get_event_loop()
            
            for recipient in recipients:
                try:
                    to_number = format_phone_number(recipient)
                    message = await loop.run_in_executor(
                        self.executor,
                        lambda r=to_number: self.client.messages.create(
                            body=message_body,
                            from_=from_number,
                            to=r
                        )
                    )
                    
                    results.append({
                        'to': to_number,
                        'message_sid': message.sid,
                        'status': message.status,
                        'success': True
                    })
                    
                except Exception as e:
                    results.append({
                        'to': recipient,
                        'error': str(e),
                        'success': False
                    })
            
            success_count = sum(1 for r in results if r['success'])
            
            return self._create_success_result({
                'total_sent': len(recipients),
                'successful': success_count,
                'failed': len(recipients) - success_count,
                'results': results
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to send bulk SMS: {str(e)}")
    
    async def _get_message_history(self, params: Dict[str, Any]) -> ToolResult:
        """Get SMS message history"""
        try:
            limit = params.get("limit", 20)
            to_number = params.get("to")
            from_number = params.get("from_number")
            
            filter_params = {'limit': limit}
            if to_number:
                filter_params['to'] = format_phone_number(to_number)
            if from_number:
                filter_params['from_'] = format_phone_number(from_number)
            
            loop = asyncio.get_event_loop()
            messages = await loop.run_in_executor(
                self.executor,
                lambda: list(self.client.messages.list(**filter_params))
            )
            
            message_data = []
            for msg in messages:
                message_data.append({
                    'sid': msg.sid,
                    'from': msg.from_,
                    'to': msg.to,
                    'body': msg.body,
                    'status': msg.status,
                    'direction': msg.direction,
                    'date_created': msg.date_created.isoformat() if msg.date_created else None,
                    'date_sent': msg.date_sent.isoformat() if msg.date_sent else None,
                    'price': msg.price
                })
            
            return self._create_success_result({
                'messages': message_data,
                'count': len(message_data)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get message history: {str(e)}")
    
    async def _get_call_history(self, params: Dict[str, Any]) -> ToolResult:
        """Get call history"""
        try:
            limit = params.get("limit", 20)
            to_number = params.get("to")
            from_number = params.get("from_number")
            
            filter_params = {'limit': limit}
            if to_number:
                filter_params['to'] = format_phone_number(to_number)
            if from_number:
                filter_params['from_'] = format_phone_number(from_number)
            
            loop = asyncio.get_event_loop()
            calls = await loop.run_in_executor(
                self.executor,
                lambda: list(self.client.calls.list(**filter_params))
            )
            
            call_data = []
            for call in calls:
                # Safely get start_time
                start_time = getattr(call, 'start_time', None)
                start_time_iso = start_time.isoformat() if start_time else None
                
                # Safely get end_time  
                end_time = getattr(call, 'end_time', None)
                end_time_iso = end_time.isoformat() if end_time else None
                
                call_data.append({
                    'sid': call.sid,
                    'from': getattr(call, 'from_', getattr(call, 'from', 'unknown')),
                    'to': call.to,
                    'status': call.status,
                    'direction': getattr(call, 'direction', 'unknown'),
                    'duration': getattr(call, 'duration', None),
                    'date_created': call.date_created.isoformat() if call.date_created else None,
                    'start_time': start_time_iso,
                    'end_time': end_time_iso,
                    'price': getattr(call, 'price', None)
                })
            
            return self._create_success_result({
                'calls': call_data,
                'count': len(call_data)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get call history: {str(e)}")
    
    async def _check_phone_number(self, params: Dict[str, Any]) -> ToolResult:
        """Check phone number validity and carrier info"""
        error = validate_required_params(params, ["phone_number"])
        if error:
            return self._create_error_result(error)
        
        try:
            phone_number = format_phone_number(params["phone_number"])
            
            loop = asyncio.get_event_loop()
            phone_info = await loop.run_in_executor(
                self.executor,
                lambda: self.client.lookups.v1.phone_numbers(phone_number).fetch(type=['carrier'])
            )
            
            return self._create_success_result({
                'phone_number': phone_info.phone_number,
                'country_code': phone_info.country_code,
                'national_format': phone_info.national_format,
                'carrier_info': phone_info.carrier,
                'valid': True
            })
            
        except Exception as e:
            return self._create_error_result(f"Phone number validation failed: {str(e)}")
    
    async def _get_account_usage(self, params: Dict[str, Any]) -> ToolResult:
        """Get account usage statistics"""
        try:
            loop = asyncio.get_event_loop()
            
            # Get account balance
            balance = await loop.run_in_executor(
                self.executor,
                lambda: self.client.api.accounts(self.account_sid).balance.fetch()
            )
            
            # Get recent usage (last 30 days)
            usage_records = await loop.run_in_executor(
                self.executor,
                lambda: list(self.client.usage.records.list(limit=50))
            )
            
            usage_summary = {}
            for record in usage_records:
                category = record.category
                if category in usage_summary:
                    usage_summary[category]['usage'] += float(record.usage or 0)
                    usage_summary[category]['price'] += float(record.price or 0)
                else:
                    usage_summary[category] = {
                        'usage': float(record.usage or 0),
                        'price': float(record.price or 0),
                        'units': getattr(record, 'units', 'unknown')
                    }
            
            return self._create_success_result({
                'account_sid': self.account_sid,
                'balance': {
                    'currency': balance.currency,
                    'balance': balance.balance
                },
                'usage_summary': usage_summary,
                'total_records': len(usage_records)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get account usage: {str(e)}")
    
    async def _get_available_numbers(self, params: Dict[str, Any]) -> ToolResult:
        """Get available phone numbers for purchase"""
        try:
            country_code = params.get("country_code", "US")
            area_code = params.get("area_code")
            limit = params.get("limit", 10)
            
            search_params = {'limit': limit}
            if area_code:
                search_params['area_code'] = area_code
            
            loop = asyncio.get_event_loop()
            available_numbers = await loop.run_in_executor(
                self.executor,
                lambda: list(self.client.available_phone_numbers(country_code).local.list(**search_params))
            )
            
            numbers_data = []
            for number in available_numbers:
                # Safely handle capabilities which might be a dict, list, or None
                capabilities = getattr(number, 'capabilities', {})
                if isinstance(capabilities, dict):
                    caps = {
                        'voice': capabilities.get('voice', False),
                        'sms': capabilities.get('sms', False),
                        'mms': capabilities.get('mms', False)
                    }
                else:
                    caps = {'voice': False, 'sms': False, 'mms': False}
                
                numbers_data.append({
                    'phone_number': number.phone_number,
                    'friendly_name': getattr(number, 'friendly_name', 'N/A'),
                    'locality': getattr(number, 'locality', 'N/A'),
                    'region': getattr(number, 'region', 'N/A'),
                    'postal_code': getattr(number, 'postal_code', 'N/A'),
                    'iso_country': getattr(number, 'iso_country', 'N/A'),
                    'capabilities': caps
                })
            
            return self._create_success_result({
                'available_numbers': numbers_data,
                'count': len(numbers_data),
                'country_code': country_code,
                'search_criteria': search_params
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get available numbers: {str(e)}")
    
    async def _schedule_message(self, params: Dict[str, Any]) -> ToolResult:
        """Schedule a message for later delivery"""
        # Note: Twilio doesn't have native scheduling, so this would typically
        # integrate with a job scheduler or be implemented as a future enhancement
        return self._create_error_result("Message scheduling not yet implemented. Use external scheduler with send_sms action.")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
