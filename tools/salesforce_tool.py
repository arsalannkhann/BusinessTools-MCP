"""
Salesforce CRM integration tool
Handles leads, opportunities, accounts, and custom objects
"""

import asyncio
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import mcp.types as types
from simple_salesforce import Salesforce, SalesforceError
from .base import SalesTool, ToolResult, validate_required_params

class SalesforceTool(SalesTool):
    """Salesforce CRM operations"""
    
    def __init__(self):
        super().__init__("salesforce", "Salesforce CRM integration for leads, opportunities, and accounts")
        self.sf: Optional[Salesforce] = None
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Salesforce connection"""
        try:
            username = settings.salesforce_username
            password = settings.salesforce_password
            security_token = settings.salesforce_security_token
            domain = settings.salesforce_domain
            
            if not all([username, password, security_token]):
                self.logger.warning("Salesforce credentials not configured")
                return False
            
            # Initialize Salesforce client in thread pool
            loop = asyncio.get_event_loop()
            self.sf = await loop.run_in_executor(
                self.executor,
                self._create_sf_client,
                username, password, security_token, domain
            )
            
            # Test connection
            await loop.run_in_executor(
                self.executor,
                lambda: self.sf.query("SELECT Id FROM User LIMIT 1")
            )
            
            self.logger.info("Salesforce connection validated")
            return True
            
        except Exception as e:
            self.logger.error(f"Salesforce initialization failed: {e}")
            return False
    
    def _create_sf_client(self, username, password, security_token, domain):
        """Create Salesforce client (sync operation)"""
        return Salesforce(
            username=username,
            password=password,
            security_token=security_token,
            domain=domain
        )
    
    async def execute(self, action: str, params: Dict[str, Any]) -> ToolResult:
        """Execute Salesforce operations"""
        if not self.sf:
            return self._create_error_result("Salesforce not initialized")
        
        try:
            if action == "create_lead":
                return await self._create_lead(params)
            elif action == "get_lead":
                return await self._get_lead(params)
            elif action == "update_lead":
                return await self._update_lead(params)
            elif action == "list_leads":
                return await self._list_leads(params)
            elif action == "convert_lead":
                return await self._convert_lead(params)
            elif action == "create_opportunity":
                return await self._create_opportunity(params)
            elif action == "get_opportunity":
                return await self._get_opportunity(params)
            elif action == "list_opportunities":
                return await self._list_opportunities(params)
            elif action == "create_account":
                return await self._create_account(params)
            elif action == "get_account":
                return await self._get_account(params)
            elif action == "search":
                return await self._search(params)
            elif action == "query":
                return await self._custom_query(params)
            else:
                return self._create_error_result(f"Unknown action: {action}")
        
        except Exception as e:
            return self._create_error_result(f"Salesforce operation failed: {str(e)}")
    
    async def _create_lead(self, params: Dict[str, Any]) -> ToolResult:
        """Create a new lead"""
        error = validate_required_params(params, ["LastName"])
        if error:
            return self._create_error_result(error)
        
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.Lead.create(params)
            )
            
            return self._create_success_result({
                "lead_id": result["id"],
                "success": result["success"]
            })
            
        except SalesforceError as e:
            return self._create_error_result(f"Failed to create lead: {str(e)}")
    
    async def _get_lead(self, params: Dict[str, Any]) -> ToolResult:
        """Get lead by ID"""
        error = validate_required_params(params, ["lead_id"])
        if error:
            return self._create_error_result(error)
        
        loop = asyncio.get_event_loop()
        lead_id = params["lead_id"]
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.Lead.get(lead_id)
            )
            
            return self._create_success_result(dict(result))
            
        except SalesforceError as e:
            return self._create_error_result(f"Lead not found: {str(e)}")
    
    async def _update_lead(self, params: Dict[str, Any]) -> ToolResult:
        """Update lead"""
        error = validate_required_params(params, ["lead_id"])
        if error:
            return self._create_error_result(error)
        
        lead_id = params.pop("lead_id")
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.Lead.update(lead_id, params)
            )
            
            return self._create_success_result({
                "lead_id": lead_id,
                "success": result == 204  # HTTP 204 No Content indicates success
            })
            
        except SalesforceError as e:
            return self._create_error_result(f"Failed to update lead: {str(e)}")
    
    async def _list_leads(self, params: Dict[str, Any]) -> ToolResult:
        """List leads with SOQL query"""
        limit = params.get("limit", 100)
        where_clause = params.get("where", "")
        order_by = params.get("order_by", "CreatedDate DESC")
        
        query = f"SELECT Id, FirstName, LastName, Email, Company, Status, CreatedDate FROM Lead"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" ORDER BY {order_by} LIMIT {limit}"
        
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.query(query)
            )
            
            return self._create_success_result({
                "leads": result["records"],
                "total_size": result["totalSize"],
                "done": result["done"]
            })
            
        except SalesforceError as e:
            return self._create_error_result(f"Failed to list leads: {str(e)}")
    
    async def _convert_lead(self, params: Dict[str, Any]) -> ToolResult:
        """Convert lead to opportunity"""
        error = validate_required_params(params, ["lead_id"])
        if error:
            return self._create_error_result(error)
        
        lead_id = params["lead_id"]
        convert_data = {
            "leadId": lead_id,
            "convertedStatus": params.get("converted_status", "Closed - Converted"),
            "doNotCreateOpportunity": params.get("do_not_create_opportunity", False)
        }
        
        if "account_id" in params:
            convert_data["accountId"] = params["account_id"]
        if "contact_id" in params:
            convert_data["contactId"] = params["contact_id"]
        if "opportunity_name" in params:
            convert_data["opportunityName"] = params["opportunity_name"]
        
        loop = asyncio.get_event_loop()
        
        try:
            # Use REST API for lead conversion
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.restful(f"sobjects/Lead/{lead_id}/", method="POST", json=convert_data)
            )
            
            return self._create_success_result(result)
            
        except SalesforceError as e:
            return self._create_error_result(f"Failed to convert lead: {str(e)}")
    
    async def _create_opportunity(self, params: Dict[str, Any]) -> ToolResult:
        """Create a new opportunity"""
        error = validate_required_params(params, ["Name", "StageName", "CloseDate"])
        if error:
            return self._create_error_result(error)
        
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.Opportunity.create(params)
            )
            
            return self._create_success_result({
                "opportunity_id": result["id"],
                "success": result["success"]
            })
            
        except SalesforceError as e:
            return self._create_error_result(f"Failed to create opportunity: {str(e)}")
    
    async def _get_opportunity(self, params: Dict[str, Any]) -> ToolResult:
        """Get opportunity by ID"""
        error = validate_required_params(params, ["opportunity_id"])
        if error:
            return self._create_error_result(error)
        
        loop = asyncio.get_event_loop()
        opportunity_id = params["opportunity_id"]
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.Opportunity.get(opportunity_id)
            )
            
            return self._create_success_result(dict(result))
            
        except SalesforceError as e:
            return self._create_error_result(f"Opportunity not found: {str(e)}")
    
    async def _list_opportunities(self, params: Dict[str, Any]) -> ToolResult:
        """List opportunities"""
        limit = params.get("limit", 100)
        where_clause = params.get("where", "")
        order_by = params.get("order_by", "CreatedDate DESC")
        
        query = f"SELECT Id, Name, StageName, Amount, CloseDate, AccountId, CreatedDate FROM Opportunity"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" ORDER BY {order_by} LIMIT {limit}"
        
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.query(query)
            )
            
            return self._create_success_result({
                "opportunities": result["records"],
                "total_size": result["totalSize"],
                "done": result["done"]
            })
            
        except SalesforceError as e:
            return self._create_error_result(f"Failed to list opportunities: {str(e)}")
    
    async def _create_account(self, params: Dict[str, Any]) -> ToolResult:
        """Create a new account"""
        error = validate_required_params(params, ["Name"])
        if error:
            return self._create_error_result(error)
        
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.Account.create(params)
            )
            
            return self._create_success_result({
                "account_id": result["id"],
                "success": result["success"]
            })
            
        except SalesforceError as e:
            return self._create_error_result(f"Failed to create account: {str(e)}")
    
    async def _get_account(self, params: Dict[str, Any]) -> ToolResult:
        """Get account by ID"""
        error = validate_required_params(params, ["account_id"])
        if error:
            return self._create_error_result(error)
        
        loop = asyncio.get_event_loop()
        account_id = params["account_id"]
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.Account.get(account_id)
            )
            
            return self._create_success_result(dict(result))
            
        except SalesforceError as e:
            return self._create_error_result(f"Account not found: {str(e)}")
    
    async def _search(self, params: Dict[str, Any]) -> ToolResult:
        """Search using SOSL"""
        error = validate_required_params(params, ["search_term"])
        if error:
            return self._create_error_result(error)
        
        search_term = params["search_term"]
        objects = params.get("objects", ["Lead", "Contact", "Account", "Opportunity"])
        limit = params.get("limit", 50)
        
        # Build SOSL query
        returning_clause = " AND ".join([f"{obj}(Id, Name)" for obj in objects])
        sosl_query = f"FIND {{{search_term}}} IN ALL FIELDS RETURNING {returning_clause} LIMIT {limit}"
        
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.search(sosl_query)
            )
            
            return self._create_success_result({
                "search_records": result.get("searchRecords", []),
                "total": len(result.get("searchRecords", []))
            })
            
        except SalesforceError as e:
            return self._create_error_result(f"Search failed: {str(e)}")
    
    async def _custom_query(self, params: Dict[str, Any]) -> ToolResult:
        """Execute custom SOQL query"""
        error = validate_required_params(params, ["query"])
        if error:
            return self._create_error_result(error)
        
        query = params["query"]
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sf.query(query)
            )
            
            return self._create_success_result({
                "records": result["records"],
                "total_size": result["totalSize"],
                "done": result["done"]
            })
            
        except SalesforceError as e:
            return self._create_error_result(f"Query failed: {str(e)}")
    
    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition"""
        return types.Tool(
            name="salesforce",
            description="Salesforce CRM operations for leads, opportunities, and accounts",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "create_lead", "get_lead", "update_lead", "list_leads", "convert_lead",
                            "create_opportunity", "get_opportunity", "list_opportunities",
                            "create_account", "get_account", "search", "query"
                        ],
                        "description": "The action to perform"
                    },
                    "lead_id": {"type": "string", "description": "Lead ID"},
                    "opportunity_id": {"type": "string", "description": "Opportunity ID"},
                    "account_id": {"type": "string", "description": "Account ID"},
                    "query": {"type": "string", "description": "SOQL query or search term"},
                    "search_term": {"type": "string", "description": "Search term for SOSL"},
                    "objects": {"type": "array", "items": {"type": "string"}, "description": "Objects to search"},
                    "where": {"type": "string", "description": "WHERE clause for queries"},
                    "order_by": {"type": "string", "description": "ORDER BY clause"},
                    "limit": {"type": "integer", "description": "Results limit", "default": 100},
                    "Name": {"type": "string", "description": "Name field for records"},
                    "LastName": {"type": "string", "description": "Last name for leads"},
                    "FirstName": {"type": "string", "description": "First name for leads"},
                    "Email": {"type": "string", "description": "Email address"},
                    "Company": {"type": "string", "description": "Company name for leads"},
                    "Status": {"type": "string", "description": "Lead status"},
                    "StageName": {"type": "string", "description": "Stage name for opportunities"},
                    "CloseDate": {"type": "string", "description": "Close date for opportunities"},
                    "Amount": {"type": "number", "description": "Opportunity amount"},
                    "converted_status": {"type": "string", "description": "Status for lead conversion"},
                    "do_not_create_opportunity": {"type": "boolean", "description": "Skip opportunity creation on lead conversion"},
                    "contact_id": {"type": "string", "description": "Contact ID for lead conversion"},
                    "opportunity_name": {"type": "string", "description": "Opportunity name for lead conversion"}
                },
                "required": ["action"]
            }
        )
    
    async def cleanup(self):
        """Clean up resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
        self.logger.info("Salesforce tool cleaned up")