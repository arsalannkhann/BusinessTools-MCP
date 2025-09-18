"""
LinkedIn Sales Navigator integration tool
Handles profile searches and connection management
"""

import aiohttp
import mcp.types as types
from typing import Dict, Any, Optional
from .base import SalesTool, ToolResult, validate_required_params

class LinkedInTool(SalesTool):
    """LinkedIn Sales Navigator operations"""
    
    def __init__(self):
        super().__init__("linkedin", "LinkedIn Sales Navigator integration for profile searches")
        self.access_token: Optional[str] = None
        self.base_url = "https://api.linkedin.com/v2"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize LinkedIn connection"""
        self.access_token = settings.linkedin_access_token
        
        if not self.access_token:
            self.logger.warning("LinkedIn access token not configured")
            return False
        
        # Create HTTP session
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        self.session = aiohttp.ClientSession(headers=headers)
        
        # Test connection
        try:
            async with self.session.get(f"{self.base_url}/me") as resp:
                if resp.status == 200:
                    self.logger.info("LinkedIn connection validated")
                    return True
                else:
                    self.logger.error(f"LinkedIn validation failed: {resp.status}")
                    return False
        except Exception as e:
            self.logger.error(f"LinkedIn connection test failed: {e}")
            return False
    
    async def execute(self, action: str, params: Dict[str, Any]) -> ToolResult:
        """Execute LinkedIn operations"""
        if not self.session:
            return self._create_error_result("LinkedIn not initialized")
        
        try:
            if action == "get_profile":
                return await self._get_profile(params)
            elif action == "search_people":
                return await self._search_people(params)
            elif action == "search_companies":
                return await self._search_companies(params)
            elif action == "get_company":
                return await self._get_company(params)
            elif action == "send_message":
                return await self._send_message(params)
            elif action == "get_connections":
                return await self._get_connections(params)
            else:
                return self._create_error_result(f"Unknown action: {action}")
        
        except Exception as e:
            return self._create_error_result(f"LinkedIn operation failed: {str(e)}")
    
    async def _get_profile(self, params: Dict[str, Any]) -> ToolResult:
        """Get current user's profile"""
        fields = params.get("fields", "id,firstName,lastName,headline,positions,industry")
        
        async with self.session.get(f"{self.base_url}/me?fields=({fields})") as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result)
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to get profile: {error_data}")
    
    async def _search_people(self, params: Dict[str, Any]) -> ToolResult:
        """Search for people (limited by LinkedIn API restrictions)"""
        # Note: LinkedIn heavily restricts people search in their public API
        # This is a simplified implementation
        
        keywords = params.get("keywords", "")
        start = params.get("start", 0)
        count = params.get("count", 10)
        
        query_params = {
            "keywords": keywords,
            "start": start,
            "count": min(count, 50)  # LinkedIn API limit
        }
        
        async with self.session.get(f"{self.base_url}/peopleSearch", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "people": result.get("elements", []),
                    "paging": result.get("paging", {}),
                    "total": len(result.get("elements", []))
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to search people: {error_data}")
    
    async def _search_companies(self, params: Dict[str, Any]) -> ToolResult:
        """Search for companies"""
        keywords = params.get("keywords", "")
        start = params.get("start", 0)
        count = params.get("count", 10)
        
        query_params = {
            "keywords": keywords,
            "start": start,
            "count": min(count, 50)
        }
        
        async with self.session.get(f"{self.base_url}/companySearch", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "companies": result.get("elements", []),
                    "paging": result.get("paging", {}),
                    "total": len(result.get("elements", []))
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to search companies: {error_data}")
    
    async def _get_company(self, params: Dict[str, Any]) -> ToolResult:
        """Get company information"""
        error = validate_required_params(params, ["company_id"])
        if error:
            return self._create_error_result(error)
        
        company_id = params["company_id"]
        fields = params.get("fields", "id,name,description,website,industry,specialties,locations")
        
        async with self.session.get(f"{self.base_url}/companies/{company_id}?fields=({fields})") as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result)
            else:
                return self._create_error_result(f"Company not found: {company_id}")
    
    async def _send_message(self, params: Dict[str, Any]) -> ToolResult:
        """Send a message (requires messaging permissions)"""
        error = validate_required_params(params, ["recipient", "message"])
        if error:
            return self._create_error_result(error)
        
        data = {
            "recipients": [params["recipient"]],
            "subject": params.get("subject", ""),
            "body": params["message"]
        }
        
        async with self.session.post(f"{self.base_url}/messages", json=data) as resp:
            if resp.status == 201:
                result = await resp.json()
                return self._create_success_result({
                    "message_id": result.get("id"),
                    "sent": True,
                    "recipient": params["recipient"]
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to send message: {error_data}")
    
    async def _get_connections(self, params: Dict[str, Any]) -> ToolResult:
        """Get user's connections"""
        start = params.get("start", 0)
        count = params.get("count", 25)
        
        query_params = {
            "start": start,
            "count": min(count, 100)
        }
        
        async with self.session.get(f"{self.base_url}/connections", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "connections": result.get("values", []),
                    "total": result.get("_total", 0),
                    "start": start,
                    "count": len(result.get("values", []))
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to get connections: {error_data}")
    
    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition"""
        return types.Tool(
            name="linkedin",
            description="LinkedIn Sales Navigator operations for profile searches and connections",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "get_profile", "search_people", "search_companies", 
                            "get_company", "send_message", "get_connections"
                        ],
                        "description": "The action to perform"
                    },
                    "company_id": {"type": "string", "description": "LinkedIn company ID"},
                    "recipient": {"type": "string", "description": "Message recipient"},
                    "message": {"type": "string", "description": "Message content"},
                    "subject": {"type": "string", "description": "Message subject"},
                    "keywords": {"type": "string", "description": "Search keywords"},
                    "fields": {"type": "string", "description": "Fields to retrieve"},
                    "start": {"type": "integer", "description": "Start index", "default": 0},
                    "count": {"type": "integer", "description": "Number of results", "default": 10}
                },
                "required": ["action"]
            }
        )
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        self.logger.info("LinkedIn tool cleaned up")