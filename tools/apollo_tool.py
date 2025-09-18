"""
Apollo.io integration tool for prospecting, lead enrichment, and email campaigns
Provides comprehensive sales intelligence and outreach capabilities
"""

import json
import logging
from typing import Dict, Any, Optional, List
import aiohttp
import mcp.types as types
from .base import SalesTool, ToolResult

logger = logging.getLogger(__name__)

def validate_required_params(params: Dict[str, Any], required: List[str]) -> Optional[str]:
    """Validate required parameters"""
    missing = [param for param in required if param not in params or params[param] is None]
    if missing:
        return f"Missing required parameters: {', '.join(missing)}"
    return None

class ApolloTool(SalesTool):
    """Apollo.io sales intelligence and prospecting tool"""
    
    def __init__(self):
        super().__init__("apollo", "Apollo.io sales intelligence and prospecting")
        self.api_key: Optional[str] = None
        self.base_url = "https://api.apollo.io/v1"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Apollo.io tool"""
        self.api_key = settings.apollo_api_key
        
        if not self.api_key:
            self.logger.warning("Apollo API key not configured")
            return False
        
        # Create session with authentication
        headers = {
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key
        }
        
        self.session = aiohttp.ClientSession(headers=headers)
        
        try:
            # Verify API key
            async with self.session.get(f"{self.base_url}/auth/health") as resp:
                if resp.status == 200:
                    self.logger.info("Apollo.io API key validated successfully")
                    return True
                else:
                    self.logger.error(f"Invalid Apollo API key: {resp.status}")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to validate Apollo API key: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return self.api_key is not None
    
    async def execute(self, action: str, params: Dict[str, Any]) -> ToolResult:
        """Execute Apollo.io action"""
        if not self.session:
            return self._create_error_result("Apollo tool not initialized")
        
        try:
            # People and Contact Actions
            if action == "search_people":
                return await self._search_people(params)
            elif action == "get_person":
                return await self._get_person(params)
            elif action == "enrich_person":
                return await self._enrich_person(params)
            elif action == "create_contact":
                return await self._create_contact(params)
            elif action == "update_contact":
                return await self._update_contact(params)
            elif action == "delete_contact":
                return await self._delete_contact(params)
            
            # Account/Company Actions
            elif action == "search_organizations":
                return await self._search_organizations(params)
            elif action == "get_organization":
                return await self._get_organization(params)
            elif action == "enrich_organization":
                return await self._enrich_organization(params)
            elif action == "create_account":
                return await self._create_account(params)
            elif action == "update_account":
                return await self._update_account(params)
            
            # Email Campaign Actions
            elif action == "create_email_account":
                return await self._create_email_account(params)
            elif action == "get_email_accounts":
                return await self._get_email_accounts(params)
            elif action == "send_email":
                return await self._send_email(params)
            elif action == "create_sequence":
                return await self._create_sequence(params)
            elif action == "add_contact_to_sequence":
                return await self._add_contact_to_sequence(params)
            elif action == "get_sequences":
                return await self._get_sequences(params)
            
            # Analytics Actions
            elif action == "get_email_performance":
                return await self._get_email_performance(params)
            elif action == "get_sequence_stats":
                return await self._get_sequence_stats(params)
            
            # List Management
            elif action == "create_contact_list":
                return await self._create_contact_list(params)
            elif action == "get_contact_lists":
                return await self._get_contact_lists(params)
            elif action == "add_contacts_to_list":
                return await self._add_contacts_to_list(params)
            
            else:
                return self._create_error_result(f"Unknown action: {action}")
        
        except Exception as e:
            self.logger.error(f"Error executing Apollo action {action}: {e}")
            return self._create_error_result(f"Action failed: {str(e)}")
    
    async def _search_people(self, params: Dict[str, Any]) -> ToolResult:
        """Search for people/contacts"""
        search_data = {}
        
        # Basic search parameters
        if "q" in params:
            search_data["q"] = params["q"]
        
        # Person filters
        if "person_titles" in params:
            search_data["person_titles"] = params["person_titles"]
        if "person_locations" in params:
            search_data["person_locations"] = params["person_locations"]
        if "person_seniorities" in params:
            search_data["person_seniorities"] = params["person_seniorities"]
        if "person_departments" in params:
            search_data["person_departments"] = params["person_departments"]
        
        # Company filters
        if "organization_locations" in params:
            search_data["organization_locations"] = params["organization_locations"]
        if "organization_ids" in params:
            search_data["organization_ids"] = params["organization_ids"]
        if "organization_num_employees_ranges" in params:
            search_data["organization_num_employees_ranges"] = params["organization_num_employees_ranges"]
        if "organization_industries" in params:
            search_data["organization_industries"] = params["organization_industries"]
        
        # Pagination
        search_data["page"] = params.get("page", 1)
        search_data["per_page"] = params.get("per_page", 25)
        
        # Contact info requirements
        if params.get("prospected_by_current_team") is not None:
            search_data["prospected_by_current_team"] = params["prospected_by_current_team"]
        
        async with self.session.post(f"{self.base_url}/mixed_people/search", json=search_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "people": result.get("people", []),
                    "total_entries": result.get("total_entries", 0),
                    "page": result.get("page", 1),
                    "per_page": result.get("per_page", 25),
                    "num_fetch_result": result.get("num_fetch_result", 0)
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to search people: {error_data}")
    
    async def _get_person(self, params: Dict[str, Any]) -> ToolResult:
        """Get specific person by ID"""
        error = validate_required_params(params, ["id"])
        if error:
            return self._create_error_result(error)
        
        person_id = params["id"]
        
        async with self.session.get(f"{self.base_url}/people/{person_id}") as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result.get("person"))
            else:
                return self._create_error_result(f"Person not found: {person_id}")
    
    async def _enrich_person(self, params: Dict[str, Any]) -> ToolResult:
        """Enrich person data"""
        enrich_data = {}
        
        # Identifier options
        if "id" in params:
            enrich_data["id"] = params["id"]
        elif "email" in params:
            enrich_data["email"] = params["email"]
        elif "first_name" in params and "last_name" in params:
            enrich_data["first_name"] = params["first_name"]
            enrich_data["last_name"] = params["last_name"]
            if "organization_name" in params:
                enrich_data["organization_name"] = params["organization_name"]
            if "domain" in params:
                enrich_data["domain"] = params["domain"]
        else:
            return self._create_error_result("Must provide id, email, or name with company info")
        
        # Reveal options
        enrich_data["reveal_personal_emails"] = params.get("reveal_personal_emails", False)
        enrich_data["reveal_phone_number"] = params.get("reveal_phone_number", False)
        
        async with self.session.post(f"{self.base_url}/people/match", json=enrich_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "person": result.get("person"),
                    "match_status": result.get("match_status"),
                    "credits_consumed": result.get("credits_consumed", 0)
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to enrich person: {error_data}")
    
    async def _create_contact(self, params: Dict[str, Any]) -> ToolResult:
        """Create a new contact"""
        error = validate_required_params(params, ["first_name", "last_name"])
        if error:
            return self._create_error_result(error)
        
        contact_data = {
            "first_name": params["first_name"],
            "last_name": params["last_name"],
            "email": params.get("email"),
            "title": params.get("title"),
            "organization_name": params.get("organization_name"),
            "linkedin_url": params.get("linkedin_url"),
            "twitter_url": params.get("twitter_url"),
            "github_url": params.get("github_url"),
            "facebook_url": params.get("facebook_url"),
            "personal_phone": params.get("personal_phone"),
            "mobile_phone": params.get("mobile_phone"),
            "work_phone": params.get("work_phone"),
            "other_phone": params.get("other_phone")
        }
        
        # Remove None values
        contact_data = {k: v for k, v in contact_data.items() if v is not None}
        
        async with self.session.post(f"{self.base_url}/contacts", json=contact_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "contact": result.get("contact"),
                    "created": True
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to create contact: {error_data}")
    
    async def _update_contact(self, params: Dict[str, Any]) -> ToolResult:
        """Update existing contact"""
        error = validate_required_params(params, ["id"])
        if error:
            return self._create_error_result(error)
        
        contact_id = params["id"]
        update_data = {k: v for k, v in params.items() if k != "id" and v is not None}
        
        async with self.session.put(f"{self.base_url}/contacts/{contact_id}", json=update_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "contact": result.get("contact"),
                    "updated": True
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to update contact: {error_data}")
    
    async def _delete_contact(self, params: Dict[str, Any]) -> ToolResult:
        """Delete contact"""
        error = validate_required_params(params, ["id"])
        if error:
            return self._create_error_result(error)
        
        contact_id = params["id"]
        
        async with self.session.delete(f"{self.base_url}/contacts/{contact_id}") as resp:
            if resp.status == 200:
                return self._create_success_result({
                    "deleted": True,
                    "contact_id": contact_id
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to delete contact: {error_data}")
    
    async def _search_organizations(self, params: Dict[str, Any]) -> ToolResult:
        """Search for organizations/companies"""
        search_data = {}
        
        # Basic search
        if "q" in params:
            search_data["q"] = params["q"]
        
        # Organization filters
        if "organization_locations" in params:
            search_data["organization_locations"] = params["organization_locations"]
        if "organization_num_employees_ranges" in params:
            search_data["organization_num_employees_ranges"] = params["organization_num_employees_ranges"]
        if "organization_industries" in params:
            search_data["organization_industries"] = params["organization_industries"]
        if "organization_keywords" in params:
            search_data["organization_keywords"] = params["organization_keywords"]
        if "organization_founded_year_ranges" in params:
            search_data["organization_founded_year_ranges"] = params["organization_founded_year_ranges"]
        
        # Technology filters
        if "technologies" in params:
            search_data["technologies"] = params["technologies"]
        
        # Pagination
        search_data["page"] = params.get("page", 1)
        search_data["per_page"] = params.get("per_page", 25)
        
        async with self.session.post(f"{self.base_url}/mixed_companies/search", json=search_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "organizations": result.get("organizations", []),
                    "total_entries": result.get("total_entries", 0),
                    "page": result.get("page", 1),
                    "per_page": result.get("per_page", 25)
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to search organizations: {error_data}")
    
    async def _get_organization(self, params: Dict[str, Any]) -> ToolResult:
        """Get specific organization by ID"""
        error = validate_required_params(params, ["id"])
        if error:
            return self._create_error_result(error)
        
        org_id = params["id"]
        
        async with self.session.get(f"{self.base_url}/organizations/{org_id}") as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result.get("organization"))
            else:
                return self._create_error_result(f"Organization not found: {org_id}")
    
    async def _enrich_organization(self, params: Dict[str, Any]) -> ToolResult:
        """Enrich organization data"""
        enrich_data = {}
        
        if "domain" in params:
            enrich_data["domain"] = params["domain"]
        elif "name" in params:
            enrich_data["name"] = params["name"]
        else:
            return self._create_error_result("Must provide domain or name")
        
        async with self.session.post(f"{self.base_url}/organizations/enrich", json=enrich_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "organization": result.get("organization"),
                    "credits_consumed": result.get("credits_consumed", 0)
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to enrich organization: {error_data}")
    
    async def _create_account(self, params: Dict[str, Any]) -> ToolResult:
        """Create a new account"""
        error = validate_required_params(params, ["name"])
        if error:
            return self._create_error_result(error)
        
        account_data = {
            "name": params["name"],
            "domain": params.get("domain"),
            "phone_number": params.get("phone_number"),
            "logo_url": params.get("logo_url"),
            "crunchbase_url": params.get("crunchbase_url"),
            "linkedin_url": params.get("linkedin_url"),
            "twitter_url": params.get("twitter_url"),
            "blog_url": params.get("blog_url")
        }
        
        # Remove None values
        account_data = {k: v for k, v in account_data.items() if v is not None}
        
        async with self.session.post(f"{self.base_url}/accounts", json=account_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "account": result.get("account"),
                    "created": True
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to create account: {error_data}")
    
    async def _update_account(self, params: Dict[str, Any]) -> ToolResult:
        """Update existing account"""
        error = validate_required_params(params, ["id"])
        if error:
            return self._create_error_result(error)
        
        account_id = params["id"]
        update_data = {k: v for k, v in params.items() if k != "id" and v is not None}
        
        async with self.session.put(f"{self.base_url}/accounts/{account_id}", json=update_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "account": result.get("account"),
                    "updated": True
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to update account: {error_data}")
    
    async def _send_email(self, params: Dict[str, Any]) -> ToolResult:
        """Send email to contacts"""
        error = validate_required_params(params, ["email_account_id", "recipients", "subject", "body"])
        if error:
            return self._create_error_result(error)
        
        email_data = {
            "email_account_id": params["email_account_id"],
            "recipients": params["recipients"],  # List of email addresses
            "subject": params["subject"],
            "body": params["body"],
            "send_at": params.get("send_at"),  # ISO timestamp for scheduling
            "track_opens": params.get("track_opens", True),
            "track_clicks": params.get("track_clicks", True)
        }
        
        async with self.session.post(f"{self.base_url}/emails", json=email_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "email": result.get("email"),
                    "sent": True
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to send email: {error_data}")
    
    async def _get_email_accounts(self, params: Dict[str, Any]) -> ToolResult:
        """Get email accounts"""
        async with self.session.get(f"{self.base_url}/email_accounts") as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "email_accounts": result.get("email_accounts", [])
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to get email accounts: {error_data}")
    
    async def _create_sequence(self, params: Dict[str, Any]) -> ToolResult:
        """Create email sequence"""
        error = validate_required_params(params, ["name", "steps"])
        if error:
            return self._create_error_result(error)
        
        sequence_data = {
            "name": params["name"],
            "steps": params["steps"],  # List of step objects
            "active": params.get("active", True),
            "max_bounces": params.get("max_bounces", 5)
        }
        
        async with self.session.post(f"{self.base_url}/sequences", json=sequence_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "sequence": result.get("sequence"),
                    "created": True
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to create sequence: {error_data}")
    
    async def _add_contact_to_sequence(self, params: Dict[str, Any]) -> ToolResult:
        """Add contact to sequence"""
        error = validate_required_params(params, ["sequence_id", "contact_ids"])
        if error:
            return self._create_error_result(error)
        
        data = {
            "contact_ids": params["contact_ids"],  # List of contact IDs
            "sequence_id": params["sequence_id"],
            "email_account_id": params.get("email_account_id")
        }
        
        async with self.session.post(f"{self.base_url}/sequences/add_contact_ids", json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "contacts_added": result.get("contacts", []),
                    "sequence_id": params["sequence_id"]
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to add contacts to sequence: {error_data}")
    
    async def _get_sequences(self, params: Dict[str, Any]) -> ToolResult:
        """Get email sequences"""
        query_params = {
            "page": params.get("page", 1),
            "per_page": params.get("per_page", 25)
        }
        
        async with self.session.get(f"{self.base_url}/sequences", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "sequences": result.get("sequences", []),
                    "total_entries": result.get("total_entries", 0)
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to get sequences: {error_data}")
    
    async def _get_email_performance(self, params: Dict[str, Any]) -> ToolResult:
        """Get email performance analytics"""
        query_params = {}
        
        if "start_date" in params:
            query_params["start_date"] = params["start_date"]
        if "end_date" in params:
            query_params["end_date"] = params["end_date"]
        if "email_account_id" in params:
            query_params["email_account_id"] = params["email_account_id"]
        
        async with self.session.get(f"{self.base_url}/analytics/email_performance", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result)
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to get email performance: {error_data}")
    
    async def _get_sequence_stats(self, params: Dict[str, Any]) -> ToolResult:
        """Get sequence statistics"""
        error = validate_required_params(params, ["sequence_id"])
        if error:
            return self._create_error_result(error)
        
        sequence_id = params["sequence_id"]
        
        async with self.session.get(f"{self.base_url}/sequences/{sequence_id}/stats") as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result.get("stats"))
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to get sequence stats: {error_data}")
    
    async def _create_contact_list(self, params: Dict[str, Any]) -> ToolResult:
        """Create contact list"""
        error = validate_required_params(params, ["name"])
        if error:
            return self._create_error_result(error)
        
        list_data = {
            "name": params["name"],
            "description": params.get("description", "")
        }
        
        async with self.session.post(f"{self.base_url}/contact_lists", json=list_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "contact_list": result.get("contact_list"),
                    "created": True
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to create contact list: {error_data}")
    
    async def _get_contact_lists(self, params: Dict[str, Any]) -> ToolResult:
        """Get contact lists"""
        query_params = {
            "page": params.get("page", 1),
            "per_page": params.get("per_page", 25)
        }
        
        async with self.session.get(f"{self.base_url}/contact_lists", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "contact_lists": result.get("contact_lists", []),
                    "total_entries": result.get("total_entries", 0)
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to get contact lists: {error_data}")
    
    async def _add_contacts_to_list(self, params: Dict[str, Any]) -> ToolResult:
        """Add contacts to list"""
        error = validate_required_params(params, ["contact_list_id", "contact_ids"])
        if error:
            return self._create_error_result(error)
        
        data = {
            "contact_ids": params["contact_ids"]  # List of contact IDs
        }
        
        list_id = params["contact_list_id"]
        
        async with self.session.post(f"{self.base_url}/contact_lists/{list_id}/add_contacts", json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "contacts_added": len(params["contact_ids"]),
                    "contact_list_id": list_id
                })
            else:
                error_data = await resp.text()
                return self._create_error_result(f"Failed to add contacts to list: {error_data}")
    
    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition"""
        return types.Tool(
            name="apollo",
            description="Apollo.io sales intelligence, prospecting, and email outreach platform",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            # People/Contact actions
                            "search_people", "get_person", "enrich_person", "create_contact", "update_contact", "delete_contact",
                            # Organization actions
                            "search_organizations", "get_organization", "enrich_organization", "create_account", "update_account",
                            # Email actions
                            "create_email_account", "get_email_accounts", "send_email",
                            # Sequence actions
                            "create_sequence", "add_contact_to_sequence", "get_sequences",
                            # Analytics
                            "get_email_performance", "get_sequence_stats",
                            # List management
                            "create_contact_list", "get_contact_lists", "add_contacts_to_list"
                        ],
                        "description": "The action to perform"
                    },
                    
                    # Common parameters
                    "id": {"type": "string", "description": "Record ID"},
                    "page": {"type": "integer", "description": "Page number", "default": 1},
                    "per_page": {"type": "integer", "description": "Results per page", "default": 25},
                    "q": {"type": "string", "description": "Search query"},
                    
                    # Person search parameters
                    "person_titles": {"type": "array", "items": {"type": "string"}, "description": "Job titles"},
                    "person_locations": {"type": "array", "items": {"type": "string"}, "description": "Person locations"},
                    "person_seniorities": {"type": "array", "items": {"type": "string"}, "description": "Seniority levels"},
                    "person_departments": {"type": "array", "items": {"type": "string"}, "description": "Departments"},
                    
                    # Organization search parameters
                    "organization_locations": {"type": "array", "items": {"type": "string"}, "description": "Company locations"},
                    "organization_ids": {"type": "array", "items": {"type": "string"}, "description": "Organization IDs"},
                    "organization_num_employees_ranges": {"type": "array", "items": {"type": "string"}, "description": "Employee count ranges"},
                    "organization_industries": {"type": "array", "items": {"type": "string"}, "description": "Industries"},
                    "organization_keywords": {"type": "array", "items": {"type": "string"}, "description": "Company keywords"},
                    "organization_founded_year_ranges": {"type": "array", "items": {"type": "string"}, "description": "Founded year ranges"},
                    "technologies": {"type": "array", "items": {"type": "string"}, "description": "Technologies used"},
                    
                    # Contact/Person data
                    "email": {"type": "string", "description": "Email address"},
                    "first_name": {"type": "string", "description": "First name"},
                    "last_name": {"type": "string", "description": "Last name"},
                    "title": {"type": "string", "description": "Job title"},
                    "organization_name": {"type": "string", "description": "Company name"},
                    "domain": {"type": "string", "description": "Company domain"},
                    "linkedin_url": {"type": "string", "description": "LinkedIn profile URL"},
                    "twitter_url": {"type": "string", "description": "Twitter profile URL"},
                    "github_url": {"type": "string", "description": "GitHub profile URL"},
                    "facebook_url": {"type": "string", "description": "Facebook profile URL"},
                    "personal_phone": {"type": "string", "description": "Personal phone number"},
                    "mobile_phone": {"type": "string", "description": "Mobile phone number"},
                    "work_phone": {"type": "string", "description": "Work phone number"},
                    "other_phone": {"type": "string", "description": "Other phone number"},
                    
                    # Enrichment options
                    "reveal_personal_emails": {"type": "boolean", "description": "Reveal personal email addresses", "default": false},
                    "reveal_phone_number": {"type": "boolean", "description": "Reveal phone numbers", "default": false},
                    
                    # Account/Organization data
                    "name": {"type": "string", "description": "Organization name"},
                    "phone_number": {"type": "string", "description": "Organization phone"},
                    "logo_url": {"type": "string", "description": "Company logo URL"},
                    "crunchbase_url": {"type": "string", "description": "Crunchbase URL"},
                    "blog_url": {"type": "string", "description": "Company blog URL"},
                    
                    # Email parameters
                    "email_account_id": {"type": "string", "description": "Email account ID"},
                    "recipients": {"type": "array", "items": {"type": "string"}, "description": "Recipient email addresses"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"},
                    "send_at": {"type": "string", "description": "Schedule send time (ISO 8601)"},
                    "track_opens": {"type": "boolean", "description": "Track email opens", "default": true},
                    "track_clicks": {"type": "boolean", "description": "Track link clicks", "default": true},
                    
                    # Sequence parameters
                    "sequence_id": {"type": "string", "description": "Email sequence ID"},
                    "contact_ids": {"type": "array", "items": {"type": "string"}, "description": "List of contact IDs"},
                    "steps": {"type": "array", "description": "Sequence steps configuration"},
                    "active": {"type": "boolean", "description": "Sequence active status", "default": true},
                    "max_bounces": {"type": "integer", "description": "Maximum bounces allowed", "default": 5},
                    
                    # Analytics parameters
                    "start_date": {"type": "string", "description": "Start date for analytics (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date for analytics (YYYY-MM-DD)"},
                    
                    # List management
                    "contact_list_id": {"type": "string", "description": "Contact list ID"},
                    "description": {"type": "string", "description": "List or item description"},
                    
                    # Filters
                    "prospected_by_current_team": {"type": "boolean", "description": "Filter by team prospecting status"}
                },
                "required": ["action"]
            }
        )
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        self.logger.info("Apollo tool cleaned up")