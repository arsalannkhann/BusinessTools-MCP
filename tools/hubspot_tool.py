"""HubSpot integration tool
Handles HubSpot CRM operations"""

from typing import Any

import aiohttp
from mcp import types

from .base import SalesTool, ToolResult, validate_required_params


class HubSpotTool(SalesTool):
    """HubSpot CRM operations"""

    def __init__(self):
        super().__init__("hubspot", "HubSpot CRM integration for contact and deal management")
        self.access_token = None
        self.base_url = "https://api.hubapi.com"
        self.session = None

    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize HubSpot connection"""
        self.access_token = settings.hubspot_access_token

        if not self.access_token:
            self.logger.warning("HubSpot access token not configured")
            return False

        # Create aiohttp session
        self.session = aiohttp.ClientSession(headers={
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        })

        # Test connection
        try:
            async with self.session.get(f"{self.base_url}/crm/v3/objects/contacts", params={"limit": 1}) as resp:
                if resp.status == 200:
                    self.logger.info("HubSpot API connection validated")
                    return True
                self.logger.error(f"HubSpot API test failed: {resp.status}")
                return False
        except Exception as e:
            self.logger.error(f"HubSpot API initialization failed: {e}")
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute HubSpot operations"""
        try:
            if action == "get_account":
                return await self._get_account(params)
            if action == "create_contact":
                return await self._create_contact(params)
            if action == "get_contact":
                return await self._get_contact(params)
            if action == "update_contact":
                return await self._update_contact(params)
            if action == "search_contacts":
                return await self._search_contacts(params)
            if action == "create_deal":
                return await self._create_deal(params)
            if action == "get_deal":
                return await self._get_deal(params)
            if action == "update_deal":
                return await self._update_deal(params)
            if action == "search_deals":
                return await self._search_deals(params)
            if action == "create_company":
                return await self._create_company(params)
            if action == "get_company":
                return await self._get_company(params)
            return self._create_error_result(f"Unknown action: {action}")

        except Exception as e:
            return self._create_error_result(f"HubSpot operation failed: {e!s}")

    def _ensure_session(self):
        """Ensure session is available"""
        if not self.session:
            raise ValueError("HubSpot session not initialized")
        return self.session

    async def _get_account(self, params: dict[str, Any]) -> ToolResult:
        """Get HubSpot account information"""
        try:
            session = self._ensure_session()
            async with session.get(f"{self.base_url}/integrations/v1/me") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return self._create_success_result({
                        "account_id": result.get("portalId"),
                        "domain": result.get("portalDomain", ""),
                        "name": result.get("portalName", ""),
                        "currency": result.get("currency", ""),
                        "time_zone": result.get("timeZone", ""),
                        "authenticated": True
                    })
                error_data = await resp.text()
                return self._create_error_result(f"Failed to get account info: {error_data}")
        except Exception as e:
            return self._create_error_result(f"Account info request failed: {e!s}")

    async def _create_contact(self, params: dict[str, Any]) -> ToolResult:
        """Create a new contact"""
        if "properties" not in params:
            return self._create_error_result("Missing required parameter: properties")

        data = {"properties": params["properties"]}

        async with self.session.post(f"{self.base_url}/crm/v3/objects/contacts", json=data) as resp:
            if resp.status == 201:
                result = await resp.json()
                return self._create_success_result({
                    "id": result.get("id"),
                    "properties": result.get("properties", {}),
                    "created": True
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to create contact: {error_data}")

    async def _get_contact(self, params: dict[str, Any]) -> ToolResult:
        """Get contact by ID"""
        error = validate_required_params(params, ["contact_id"])
        if error:
            return self._create_error_result(error)

        contact_id = params["contact_id"]
        properties = params.get("properties", [])

        query_params = {}
        if properties:
            query_params["properties"] = ",".join(properties)

        async with self.session.get(f"{self.base_url}/crm/v3/objects/contacts/{contact_id}", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result)
            return self._create_error_result(f"Contact not found: {contact_id}")

    async def _update_contact(self, params: dict[str, Any]) -> ToolResult:
        """Update contact"""
        error = validate_required_params(params, ["contact_id", "properties"])
        if error:
            return self._create_error_result(error)

        contact_id = params["contact_id"]
        data = {"properties": params["properties"]}

        async with self.session.patch(f"{self.base_url}/crm/v3/objects/contacts/{contact_id}", json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "id": result.get("id"),
                    "properties": result.get("properties", {}),
                    "updated": True
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to update contact: {error_data}")

    async def _search_contacts(self, params: dict[str, Any]) -> ToolResult:
        """Search contacts"""
        search_data = {
            "filterGroups": [],
            "sorts": [],
            "limit": params.get("limit", 10),
            "after": params.get("after", 0),
            "properties": params.get("properties", [])
        }

        # Add filters if provided
        if "filters" in params:
            search_data["filterGroups"] = params["filters"]

        async with self.session.post(f"{self.base_url}/crm/v3/objects/contacts/search", json=search_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "contacts": result.get("results", []),
                    "total": result.get("total", 0),
                    "pagination": {
                        "next": result.get("paging", {}).get("next", {})
                    }
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to search contacts: {error_data}")

    async def _create_deal(self, params: dict[str, Any]) -> ToolResult:
        """Create a new deal"""
        if "properties" not in params:
            return self._create_error_result("Missing required parameter: properties")

        data = {"properties": params["properties"]}

        # Add associations if provided
        if "associations" in params:
            data["associations"] = params["associations"]

        async with self.session.post(f"{self.base_url}/crm/v3/objects/deals", json=data) as resp:
            if resp.status == 201:
                result = await resp.json()
                return self._create_success_result({
                    "id": result.get("id"),
                    "properties": result.get("properties", {}),
                    "created": True
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to create deal: {error_data}")

    async def _get_deal(self, params: dict[str, Any]) -> ToolResult:
        """Get deal by ID"""
        error = validate_required_params(params, ["deal_id"])
        if error:
            return self._create_error_result(error)

        deal_id = params["deal_id"]
        properties = params.get("properties", [])

        query_params = {}
        if properties:
            query_params["properties"] = ",".join(properties)

        async with self.session.get(f"{self.base_url}/crm/v3/objects/deals/{deal_id}", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result)
            return self._create_error_result(f"Deal not found: {deal_id}")

    async def _update_deal(self, params: dict[str, Any]) -> ToolResult:
        """Update deal"""
        error = validate_required_params(params, ["deal_id", "properties"])
        if error:
            return self._create_error_result(error)

        deal_id = params["deal_id"]
        data = {"properties": params["properties"]}

        async with self.session.patch(f"{self.base_url}/crm/v3/objects/deals/{deal_id}", json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "id": result.get("id"),
                    "properties": result.get("properties", {}),
                    "updated": True
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to update deal: {error_data}")

    async def _search_deals(self, params: dict[str, Any]) -> ToolResult:
        """Search deals"""
        search_data = {
            "filterGroups": [],
            "sorts": [],
            "limit": params.get("limit", 10),
            "after": params.get("after", 0),
            "properties": params.get("properties", [])
        }

        # Add filters if provided
        if "filters" in params:
            search_data["filterGroups"] = params["filters"]

        async with self.session.post(f"{self.base_url}/crm/v3/objects/deals/search", json=search_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "deals": result.get("results", []),
                    "total": result.get("total", 0),
                    "pagination": {
                        "next": result.get("paging", {}).get("next", {})
                    }
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to search deals: {error_data}")

    async def _create_company(self, params: dict[str, Any]) -> ToolResult:
        """Create a new company"""
        if "properties" not in params:
            return self._create_error_result("Missing required parameter: properties")

        data = {"properties": params["properties"]}

        async with self.session.post(f"{self.base_url}/crm/v3/objects/companies", json=data) as resp:
            if resp.status == 201:
                result = await resp.json()
                return self._create_success_result({
                    "id": result.get("id"),
                    "properties": result.get("properties", {}),
                    "created": True
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to create company: {error_data}")

    async def _get_company(self, params: dict[str, Any]) -> ToolResult:
        """Get company by ID"""
        error = validate_required_params(params, ["company_id"])
        if error:
            return self._create_error_result(error)

        company_id = params["company_id"]
        properties = params.get("properties", [])

        query_params = {}
        if properties:
            query_params["properties"] = ",".join(properties)

        async with self.session.get(f"{self.base_url}/crm/v3/objects/companies/{company_id}", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result)
            return self._create_error_result(f"Company not found: {company_id}")

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None

    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return bool(self.access_token)

    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition for registration"""
        return types.Tool(
            name="hubspot",
            description="HubSpot CRM integration for contact and deal management",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform",
                        "enum": [
                            "get_account", "create_contact", "get_contact", "update_contact", "search_contacts",
                            "create_deal", "get_deal", "update_deal", "search_deals",
                            "create_company", "get_company"
                        ]
                    },
                    "properties": {
                        "type": "object",
                        "description": "Properties for the contact, deal, or company"
                    },
                    "contact_id": {
                        "type": "string",
                        "description": "HubSpot contact ID"
                    },
                    "deal_id": {
                        "type": "string",
                        "description": "HubSpot deal ID"
                    },
                    "company_id": {
                        "type": "string",
                        "description": "HubSpot company ID"
                    },
                    "filters": {
                        "type": "array",
                        "description": "Search filters"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return"
                    },
                    "after": {
                        "type": "integer",
                        "description": "Pagination offset"
                    }
                },
                "required": ["action"]
            }
        )
