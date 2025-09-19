"""
Outreach.io integration tool
Handles email sequences, cadences, and automated outreach campaigns
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
import mcp.types as types
import requests
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from .base import SalesTool, ToolResult, validate_required_params


@dataclass
class OutreachSequence:
    """Outreach sequence/cadence data structure"""
    id: str
    name: str
    enabled: bool
    num_steps: int
    bounce_count: int
    click_count: int
    deliver_count: int
    open_count: int
    opt_out_count: int
    reply_count: int
    schedule_count: int
    created_at: str
    updated_at: str
    tags: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class OutreachProspect:
    """Outreach prospect data structure"""
    id: str
    email: str
    first_name: str
    last_name: str
    company: str
    title: str
    stage: str
    owner_id: str
    created_at: str
    updated_at: str
    phone_numbers: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.phone_numbers is None:
            self.phone_numbers = []
        if self.tags is None:
            self.tags = []
        if self.custom_fields is None:
            self.custom_fields = {}


class OutreachTool(SalesTool):
    """Outreach.io integration for email sequences and automated outreach"""
    
    def __init__(self):
        super().__init__("outreach", "Outreach.io integration for email sequences, cadences, and automated campaigns")
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.refresh_token = None
        self.api_base_url = "https://api.outreach.io/api/v2"
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.session = None
        
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Outreach.io API connection"""
        try:
            # Get Outreach credentials from settings
            self.client_id = getattr(settings, 'outreach_client_id', None)
            self.client_secret = getattr(settings, 'outreach_client_secret', None)
            self.access_token = getattr(settings, 'outreach_access_token', None)
            self.refresh_token = getattr(settings, 'outreach_refresh_token', None)
            
            if not all([self.client_id, self.client_secret]):
                self.logger.warning("Outreach.io credentials not fully configured")
                return False
            
            # Initialize HTTP session
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/vnd.api+json',
                'Accept': 'application/vnd.api+json'
            })
            
            # Test the connection if access token is available
            if self.access_token:
                await self._test_connection()
            
            self.logger.info("Outreach.io API connection configured")
            return True
            
        except Exception as e:
            self.logger.error(f"Outreach.io initialization failed: {e}")
            return False
    
    async def _test_connection(self):
        """Test Outreach.io API connection"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._test_connection_sync
        )
    
    def _test_connection_sync(self):
        """Synchronous connection test"""
        url = f"{self.api_base_url}/accounts"
        
        response = self.session.get(url, params={'page[limit]': 1})
        if response.status_code != 200:
            raise Exception(f"Outreach.io API test failed: {response.status_code} - {response.text}")
    
    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return bool(self.client_id and self.client_secret and self.session)
    
    async def execute(self, action: str, params: Dict[str, Any]) -> ToolResult:
        """Execute Outreach.io operations"""
        try:
            if action == "create_sequence":
                return await self._create_sequence(params)
            elif action == "list_sequences":
                return await self._list_sequences(params)
            elif action == "get_sequence":
                return await self._get_sequence(params)
            elif action == "create_prospect":
                return await self._create_prospect(params)
            elif action == "add_to_sequence":
                return await self._add_to_sequence(params)
            elif action == "send_email":
                return await self._send_email(params)
            elif action == "get_analytics":
                return await self._get_analytics(params)
            elif action == "create_template":
                return await self._create_template(params)
            elif action == "list_templates":
                return await self._list_templates(params)
            elif action == "list_prospects":
                return await self._list_prospects(params)
            elif action == "update_prospect":
                return await self._update_prospect(params)
            else:
                return self._create_error_result(f"Unknown action: {action}")
        
        except Exception as e:
            return self._create_error_result(f"Outreach.io operation failed: {str(e)}")
    
    async def _create_sequence(self, params: Dict[str, Any]) -> ToolResult:
        """Create a new email sequence/cadence"""
        validation_error = validate_required_params(params, ['name'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        sequence_name = params['name']
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._create_sequence_sync(sequence_name, params)
            )
            
            # Parse sequence result
            sequence_data = self._parse_sequence_result(result)
            
            return self._create_success_result(
                data=sequence_data,
                metadata={'sequence_created': True}
            )
            
        except Exception as e:
            return self._create_error_result(f"Sequence creation failed: {e}")
    
    def _create_sequence_sync(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous sequence creation"""
        url = f"{self.api_base_url}/sequences"
        
        payload = {
            "data": {
                "type": "sequence",
                "attributes": {
                    "name": name,
                    "description": params.get('description', ''),
                    "enabled": params.get('enabled', True),
                    "tags": params.get('tags', [])
                }
            }
        }
        
        response = self.session.post(url, json=payload)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Sequence creation failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def _list_sequences(self, params: Dict[str, Any]) -> ToolResult:
        """List email sequences/cadences"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._list_sequences_sync(params)
            )
            
            sequences = [self._parse_sequence_result({'data': seq}) for seq in result.get('data', [])]
            
            return self._create_success_result(
                data=sequences,
                metadata={
                    'total_count': len(sequences),
                    'page': params.get('page', 1)
                }
            )
            
        except Exception as e:
            return self._create_error_result(f"Listing sequences failed: {e}")
    
    def _list_sequences_sync(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous sequence listing"""
        url = f"{self.api_base_url}/sequences"
        
        query_params = {
            'page[limit]': min(params.get('limit', 25), 100),
            'page[offset]': (params.get('page', 1) - 1) * min(params.get('limit', 25), 100)
        }
        
        if params.get('enabled') is not None:
            query_params['filter[enabled]'] = params['enabled']
        
        response = self.session.get(url, params=query_params)
        
        if response.status_code != 200:
            raise Exception(f"Sequence listing failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def _get_sequence(self, params: Dict[str, Any]) -> ToolResult:
        """Get specific sequence details"""
        validation_error = validate_required_params(params, ['sequence_id'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        sequence_id = params['sequence_id']
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._get_sequence_sync(sequence_id)
            )
            
            sequence_data = self._parse_sequence_result(result)
            
            return self._create_success_result(
                data=sequence_data,
                metadata={'sequence_id': sequence_id}
            )
            
        except Exception as e:
            return self._create_error_result(f"Getting sequence failed: {e}")
    
    def _get_sequence_sync(self, sequence_id: str) -> Dict[str, Any]:
        """Synchronous sequence retrieval"""
        url = f"{self.api_base_url}/sequences/{sequence_id}"
        
        response = self.session.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Sequence retrieval failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def _create_prospect(self, params: Dict[str, Any]) -> ToolResult:
        """Create a new prospect"""
        validation_error = validate_required_params(params, ['email'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._create_prospect_sync(params)
            )
            
            prospect_data = self._parse_prospect_result(result)
            
            return self._create_success_result(
                data=prospect_data,
                metadata={'prospect_created': True}
            )
            
        except Exception as e:
            return self._create_error_result(f"Prospect creation failed: {e}")
    
    def _create_prospect_sync(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous prospect creation"""
        url = f"{self.api_base_url}/prospects"
        
        payload = {
            "data": {
                "type": "prospect",
                "attributes": {
                    "emails": [params['email']],
                    "firstName": params.get('first_name', ''),
                    "lastName": params.get('last_name', ''),
                    "company": params.get('company', ''),
                    "title": params.get('title', ''),
                    "tags": params.get('tags', [])
                }
            }
        }
        
        # Add phone numbers if provided
        if params.get('phone_numbers'):
            payload['data']['attributes']['phoneNumbers'] = params['phone_numbers']
        
        response = self.session.post(url, json=payload)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Prospect creation failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def _add_to_sequence(self, params: Dict[str, Any]) -> ToolResult:
        """Add prospects to a sequence"""
        validation_error = validate_required_params(params, ['sequence_id', 'prospect_ids'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        sequence_id = params['sequence_id']
        prospect_ids = params['prospect_ids']
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._add_to_sequence_sync(sequence_id, prospect_ids)
            )
            
            return self._create_success_result(
                data={
                    'sequence_id': sequence_id,
                    'prospects_added': len(prospect_ids),
                    'sequence_states': result.get('data', [])
                },
                metadata={'prospects_added_to_sequence': True}
            )
            
        except Exception as e:
            return self._create_error_result(f"Adding to sequence failed: {e}")
    
    def _add_to_sequence_sync(self, sequence_id: str, prospect_ids: List[str]) -> Dict[str, Any]:
        """Synchronous adding prospects to sequence"""
        url = f"{self.api_base_url}/sequenceStates"
        
        # Create sequence states for each prospect
        sequence_states = []
        for prospect_id in prospect_ids:
            sequence_states.append({
                "type": "sequenceState",
                "attributes": {
                    "state": "active"
                },
                "relationships": {
                    "sequence": {
                        "data": {"type": "sequence", "id": sequence_id}
                    },
                    "prospect": {
                        "data": {"type": "prospect", "id": prospect_id}
                    }
                }
            })
        
        payload = {"data": sequence_states}
        
        response = self.session.post(url, json=payload)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Adding to sequence failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def _send_email(self, params: Dict[str, Any]) -> ToolResult:
        """Send an individual email"""
        validation_error = validate_required_params(params, ['prospect_id', 'subject', 'body'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._send_email_sync(params)
            )
            
            email_data = result.get('data', {}).get('attributes', {})
            
            return self._create_success_result(
                data={
                    'email_id': result.get('data', {}).get('id'),
                    'subject': email_data.get('subject'),
                    'state': email_data.get('state'),
                    'sent_at': email_data.get('sentAt')
                },
                metadata={'email_sent': True}
            )
            
        except Exception as e:
            return self._create_error_result(f"Email sending failed: {e}")
    
    def _send_email_sync(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous email sending"""
        url = f"{self.api_base_url}/mailings"
        
        payload = {
            "data": {
                "type": "mailing",
                "attributes": {
                    "subject": params['subject'],
                    "bodyHtml": params['body'],
                    "bodyText": params.get('body_text', ''),
                    "state": "scheduled"
                },
                "relationships": {
                    "prospect": {
                        "data": {"type": "prospect", "id": params['prospect_id']}
                    }
                }
            }
        }
        
        # Add template if provided
        if params.get('template_id'):
            payload['data']['relationships']['template'] = {
                "data": {"type": "template", "id": params['template_id']}
            }
        
        response = self.session.post(url, json=payload)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Email sending failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def _get_analytics(self, params: Dict[str, Any]) -> ToolResult:
        """Get sequence and campaign analytics"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._get_analytics_sync(params)
            )
            
            return self._create_success_result(
                data=result,
                metadata={'analytics_retrieved': True}
            )
            
        except Exception as e:
            return self._create_error_result(f"Analytics retrieval failed: {e}")
    
    def _get_analytics_sync(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get analytics synchronously"""
        # This would typically aggregate data from multiple endpoints
        analytics = {}
        
        # Get sequence stats if sequence_id provided
        if params.get('sequence_id'):
            sequence_url = f"{self.api_base_url}/sequences/{params['sequence_id']}"
            seq_response = self.session.get(sequence_url)
            if seq_response.status_code == 200:
                seq_data = seq_response.json()
                sequence_attrs = seq_data.get('data', {}).get('attributes', {})
                analytics['sequence'] = {
                    'bounce_count': sequence_attrs.get('bounceCount', 0),
                    'click_count': sequence_attrs.get('clickCount', 0),
                    'deliver_count': sequence_attrs.get('deliverCount', 0),
                    'open_count': sequence_attrs.get('openCount', 0),
                    'opt_out_count': sequence_attrs.get('optOutCount', 0),
                    'reply_count': sequence_attrs.get('replyCount', 0),
                    'schedule_count': sequence_attrs.get('scheduleCount', 0)
                }
        
        return analytics
    
    async def _create_template(self, params: Dict[str, Any]) -> ToolResult:
        """Create an email template"""
        validation_error = validate_required_params(params, ['name', 'subject', 'body'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._create_template_sync(params)
            )
            
            template_data = self._parse_template_result(result)
            
            return self._create_success_result(
                data=template_data,
                metadata={'template_created': True}
            )
            
        except Exception as e:
            return self._create_error_result(f"Template creation failed: {e}")
    
    def _create_template_sync(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous template creation"""
        url = f"{self.api_base_url}/templates"
        
        payload = {
            "data": {
                "type": "template",
                "attributes": {
                    "name": params['name'],
                    "subject": params['subject'],
                    "bodyHtml": params['body'],
                    "bodyText": params.get('body_text', ''),
                    "tags": params.get('tags', [])
                }
            }
        }
        
        response = self.session.post(url, json=payload)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Template creation failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def _list_templates(self, params: Dict[str, Any]) -> ToolResult:
        """List email templates"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._list_templates_sync(params)
            )
            
            templates = [self._parse_template_result({'data': template}) for template in result.get('data', [])]
            
            return self._create_success_result(
                data=templates,
                metadata={
                    'total_count': len(templates),
                    'page': params.get('page', 1)
                }
            )
            
        except Exception as e:
            return self._create_error_result(f"Listing templates failed: {e}")
    
    def _list_templates_sync(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous template listing"""
        url = f"{self.api_base_url}/templates"
        
        query_params = {
            'page[limit]': min(params.get('limit', 25), 100),
            'page[offset]': (params.get('page', 1) - 1) * min(params.get('limit', 25), 100)
        }
        
        response = self.session.get(url, params=query_params)
        
        if response.status_code != 200:
            raise Exception(f"Template listing failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def _list_prospects(self, params: Dict[str, Any]) -> ToolResult:
        """List prospects"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._list_prospects_sync(params)
            )
            
            prospects = [self._parse_prospect_result({'data': prospect}) for prospect in result.get('data', [])]
            
            return self._create_success_result(
                data=prospects,
                metadata={
                    'total_count': len(prospects),
                    'page': params.get('page', 1)
                }
            )
            
        except Exception as e:
            return self._create_error_result(f"Listing prospects failed: {e}")
    
    def _list_prospects_sync(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous prospect listing"""
        url = f"{self.api_base_url}/prospects"
        
        query_params = {
            'page[limit]': min(params.get('limit', 25), 100),
            'page[offset]': (params.get('page', 1) - 1) * min(params.get('limit', 25), 100)
        }
        
        if params.get('stage'):
            query_params['filter[stage]'] = params['stage']
        
        response = self.session.get(url, params=query_params)
        
        if response.status_code != 200:
            raise Exception(f"Prospect listing failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def _update_prospect(self, params: Dict[str, Any]) -> ToolResult:
        """Update an existing prospect"""
        validation_error = validate_required_params(params, ['prospect_id'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        prospect_id = params['prospect_id']
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._update_prospect_sync(prospect_id, params)
            )
            
            prospect_data = self._parse_prospect_result(result)
            
            return self._create_success_result(
                data=prospect_data,
                metadata={'prospect_updated': True}
            )
            
        except Exception as e:
            return self._create_error_result(f"Prospect update failed: {e}")
    
    def _update_prospect_sync(self, prospect_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous prospect update"""
        url = f"{self.api_base_url}/prospects/{prospect_id}"
        
        attributes = {}
        
        # Update fields if provided
        if params.get('first_name'):
            attributes['firstName'] = params['first_name']
        if params.get('last_name'):
            attributes['lastName'] = params['last_name']
        if params.get('company'):
            attributes['company'] = params['company']
        if params.get('title'):
            attributes['title'] = params['title']
        if params.get('stage'):
            attributes['stage'] = params['stage']
        if params.get('tags'):
            attributes['tags'] = params['tags']
        
        payload = {
            "data": {
                "type": "prospect",
                "id": prospect_id,
                "attributes": attributes
            }
        }
        
        response = self.session.patch(url, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Prospect update failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def _parse_sequence_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse sequence result from API"""
        data = result.get('data', {})
        attributes = data.get('attributes', {})
        
        return {
            'id': data.get('id', ''),
            'name': attributes.get('name', ''),
            'enabled': attributes.get('enabled', False),
            'num_steps': attributes.get('numSteps', 0),
            'bounce_count': attributes.get('bounceCount', 0),
            'click_count': attributes.get('clickCount', 0),
            'deliver_count': attributes.get('deliverCount', 0),
            'open_count': attributes.get('openCount', 0),
            'opt_out_count': attributes.get('optOutCount', 0),
            'reply_count': attributes.get('replyCount', 0),
            'schedule_count': attributes.get('scheduleCount', 0),
            'created_at': attributes.get('createdAt', ''),
            'updated_at': attributes.get('updatedAt', ''),
            'tags': attributes.get('tags', [])
        }
    
    def _parse_prospect_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse prospect result from API"""
        data = result.get('data', {})
        attributes = data.get('attributes', {})
        
        return {
            'id': data.get('id', ''),
            'email': attributes.get('emails', [''])[0] if attributes.get('emails') else '',
            'first_name': attributes.get('firstName', ''),
            'last_name': attributes.get('lastName', ''),
            'company': attributes.get('company', ''),
            'title': attributes.get('title', ''),
            'stage': attributes.get('stage', ''),
            'created_at': attributes.get('createdAt', ''),
            'updated_at': attributes.get('updatedAt', ''),
            'phone_numbers': attributes.get('phoneNumbers', []),
            'tags': attributes.get('tags', [])
        }
    
    def _parse_template_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse template result from API"""
        data = result.get('data', {})
        attributes = data.get('attributes', {})
        
        return {
            'id': data.get('id', ''),
            'name': attributes.get('name', ''),
            'subject': attributes.get('subject', ''),
            'body_html': attributes.get('bodyHtml', ''),
            'body_text': attributes.get('bodyText', ''),
            'created_at': attributes.get('createdAt', ''),
            'updated_at': attributes.get('updatedAt', ''),
            'tags': attributes.get('tags', [])
        }
    
    def get_mcp_tool_definition(self) -> types.Tool:
        """Return MCP tool definition for Outreach.io"""
        return types.Tool(
            name="outreach",
            description="Outreach.io integration for email sequences, cadences, and automated outreach campaigns",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "create_sequence", "list_sequences", "get_sequence",
                            "create_prospect", "list_prospects", "update_prospect",
                            "add_to_sequence", "send_email", "get_analytics",
                            "create_template", "list_templates"
                        ],
                        "description": "The Outreach.io action to perform"
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for sequence, template, or other entity"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description for sequence or template"
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether sequence is enabled"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization"
                    },
                    "sequence_id": {
                        "type": "string",
                        "description": "Sequence ID for operations"
                    },
                    "prospect_id": {
                        "type": "string",
                        "description": "Prospect ID for operations"
                    },
                    "prospect_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of prospect IDs"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address"
                    },
                    "first_name": {
                        "type": "string",
                        "description": "First name"
                    },
                    "last_name": {
                        "type": "string",
                        "description": "Last name"
                    },
                    "company": {
                        "type": "string",
                        "description": "Company name"
                    },
                    "title": {
                        "type": "string",
                        "description": "Job title"
                    },
                    "stage": {
                        "type": "string",
                        "description": "Prospect stage"
                    },
                    "phone_numbers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Phone numbers"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body HTML content"
                    },
                    "body_text": {
                        "type": "string",
                        "description": "Email body text content"
                    },
                    "template_id": {
                        "type": "string",
                        "description": "Template ID for email"
                    },
                    "page": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 1,
                        "description": "Page number for pagination"
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 25,
                        "description": "Number of results per page"
                    }
                },
                "required": ["action"]
            }
        )
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            self.session.close()
        if self.executor:
            self.executor.shutdown(wait=True)
