"""
Apollo.io integration tool
Handles email finding, contact enrichment, and prospect research
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import requests
from mcp import types

from .base import SalesTool, ToolResult, validate_required_params


@dataclass
class ApolloContact:
    """Apollo contact data structure"""
    id: str
    name: str
    email: str
    title: str
    company: str
    company_domain: str
    linkedin_url: str
    phone: str = ""
    location: str = ""
    department: str = ""
    seniority: str = ""
    email_status: str = ""
    phone_status: str = ""


@dataclass
class ApolloCompany:
    """Apollo company data structure"""
    id: str
    name: str
    domain: str
    industry: str
    size: str
    location: str
    linkedin_url: str
    website: str = ""
    phone: str = ""
    description: str = ""
    technologies: list[str] | None = None
    employee_count: int = 0
    revenue: str = ""

    def __post_init__(self):
        if self.technologies is None:
            self.technologies = []


class ApolloTool(SalesTool):
    """Apollo.io integration for email finding and contact enrichment"""

    def __init__(self):
        super().__init__("apollo", "Apollo.io integration for email finding, contact enrichment, and prospect research")
        self.api_key = None
        self.api_base_url = "https://api.apollo.io/v1"
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.session = None

    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Apollo.io API connection"""
        try:
            # Get Apollo API key from settings
            self.api_key = getattr(settings, "apollo_api_key", None)

            if not self.api_key:
                self.logger.warning("Apollo.io API key not configured")
                return False

            # Initialize HTTP session
            self.session = requests.Session()
            self.session.headers.update({
                "Cache-Control": "no-cache",
                "Content-Type": "application/json"
            })

            # Test the connection
            await self._test_connection()

            self.logger.info("Apollo.io API connection validated")
            return True

        except Exception as e:
            self.logger.error(f"Apollo.io initialization failed: {e}")
            return False

    async def _test_connection(self):
        """Test Apollo.io API connection"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._test_connection_sync
        )

    def _test_connection_sync(self):
        """Synchronous connection test"""
        url = f"{self.api_base_url}/auth/health"
        params = {"api_key": self.api_key}

        response = self.session.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"Apollo.io API test failed: {response.status_code} - {response.text}")

    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return bool(self.api_key and self.session)

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute Apollo.io operations"""
        try:
            if action == "find_email":
                return await self._find_email(params)
            if action == "search_people":
                return await self._search_people(params)
            if action == "verify_email":
                return await self._verify_email(params)
            if action == "enrich_person":
                return await self._enrich_person(params)
            if action == "search_organizations":
                return await self._search_organizations(params)
            return self._create_error_result(f"Unknown action: {action}")

        except Exception as e:
            return self._create_error_result(f"Apollo.io operation failed: {e!s}")

    async def _find_email(self, params: dict[str, Any]) -> ToolResult:
        """Find email address for a person"""
        validation_error = validate_required_params(params, ["first_name", "last_name", "domain"])
        if validation_error:
            return self._create_error_result(validation_error)

        first_name = params["first_name"]
        last_name = params["last_name"]
        domain = params["domain"]

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._find_email_sync(first_name, last_name, domain)
            )

            # Parse result
            email_data = self._parse_email_finder_result(result)

            return self._create_success_result(
                data=email_data,
                metadata={
                    "search_name": f"{first_name} {last_name}",
                    "domain": domain
                }
            )

        except Exception as e:
            return self._create_error_result(f"Email finding failed: {e}")

    def _find_email_sync(self, first_name: str, last_name: str, domain: str) -> dict[str, Any]:
        """Synchronous email finding"""
        url = f"{self.api_base_url}/email_finder"

        payload = {
            "api_key": self.api_key,
            "first_name": first_name,
            "last_name": last_name,
            "domain": domain
        }

        response = self.session.post(url, json=payload)

        if response.status_code != 200:
            raise Exception(f"Email finder failed: {response.status_code} - {response.text}")

        return response.json()

    def _parse_email_finder_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Parse email finder result"""
        contact = result.get("contact", {})

        return {
            "email": contact.get("email", ""),
            "confidence": contact.get("email_confidence", 0),
            "status": contact.get("email_status", ""),
            "verification_status": contact.get("verification_status", ""),
            "name": contact.get("name", ""),
            "title": contact.get("title", ""),
            "company": contact.get("company", ""),
            "linkedin_url": contact.get("linkedin_url", ""),
            "phone": contact.get("phone", ""),
            "department": contact.get("department", "")
        }

    async def _search_people(self, params: dict[str, Any]) -> ToolResult:
        """Search for people with filters"""
        try:
            # Build search parameters
            search_params = {
                "api_key": self.api_key,
                "page": params.get("page", 1),
                "per_page": min(params.get("per_page", 25), 200)  # Apollo limits to 200
            }

            # Add filters
            if params.get("titles"):
                search_params["person_titles"] = params["titles"]
            if params.get("company_names"):
                search_params["organization_names"] = params["company_names"]
            if params.get("locations"):
                search_params["person_locations"] = params["locations"]

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._search_people_sync(search_params)
            )

            # Parse results
            people_data = self._parse_people_search_result(result)

            return self._create_success_result(
                data=people_data,
                metadata={
                    "total_results": result.get("pagination", {}).get("total_entries", 0),
                    "page": search_params["page"],
                    "per_page": search_params["per_page"]
                }
            )

        except Exception as e:
            return self._create_error_result(f"People search failed: {e}")

    def _search_people_sync(self, search_params: dict[str, Any]) -> dict[str, Any]:
        """Synchronous people search"""
        url = f"{self.api_base_url}/mixed_people/search"

        response = self.session.post(url, json=search_params)

        if response.status_code != 200:
            raise Exception(f"People search failed: {response.status_code} - {response.text}")

        return response.json()

    def _parse_people_search_result(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse people search results"""
        people = []

        for person in result.get("people", []):
            people.append({
                "id": person.get("id", ""),
                "name": person.get("name", ""),
                "email": person.get("email", ""),
                "title": person.get("title", ""),
                "company": person.get("organization", {}).get("name", ""),
                "company_domain": person.get("organization", {}).get("primary_domain", ""),
                "linkedin_url": person.get("linkedin_url", ""),
                "phone": person.get("phone", ""),
                "location": f"{person.get('city', '')} {person.get('state', '')}".strip()
            })

        return people

    async def _verify_email(self, params: dict[str, Any]) -> ToolResult:
        """Verify email address validity"""
        validation_error = validate_required_params(params, ["email"])
        if validation_error:
            return self._create_error_result(validation_error)

        email = params["email"]

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._verify_email_sync(email)
            )

            verification_data = {
                "email": email,
                "is_valid": result.get("is_valid", False),
                "is_deliverable": result.get("is_deliverable", False),
                "confidence": result.get("confidence", 0)
            }

            return self._create_success_result(
                data=verification_data,
                metadata={"verification_performed": True}
            )

        except Exception as e:
            return self._create_error_result(f"Email verification failed: {e}")

    def _verify_email_sync(self, email: str) -> dict[str, Any]:
        """Synchronous email verification"""
        url = f"{self.api_base_url}/email_verifier"

        payload = {
            "api_key": self.api_key,
            "email": email
        }

        response = self.session.post(url, json=payload)

        if response.status_code != 200:
            raise Exception(f"Email verification failed: {response.status_code} - {response.text}")

        return response.json()

    async def _enrich_person(self, params: dict[str, Any]) -> ToolResult:
        """Enrich person data with additional information"""
        validation_error = validate_required_params(params, ["email"])
        if validation_error:
            return self._create_error_result(validation_error)

        email = params["email"]

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._enrich_person_sync(email)
            )

            # Parse person enrichment result
            person_data = self._parse_person_enrichment_result(result)

            return self._create_success_result(
                data=person_data,
                metadata={"enrichment_performed": True}
            )

        except Exception as e:
            return self._create_error_result(f"Person enrichment failed: {e}")

    def _enrich_person_sync(self, email: str) -> dict[str, Any]:
        """Synchronous person enrichment"""
        url = f"{self.api_base_url}/people/match"

        payload = {
            "api_key": self.api_key,
            "email": email
        }

        response = self.session.post(url, json=payload)

        if response.status_code != 200:
            raise Exception(f"Person enrichment failed: {response.status_code} - {response.text}")

        return response.json()

    def _parse_person_enrichment_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Parse person enrichment result"""
        person = result.get("person", {})

        return {
            "id": person.get("id", ""),
            "name": person.get("name", ""),
            "email": person.get("email", ""),
            "title": person.get("title", ""),
            "company": person.get("organization", {}).get("name", ""),
            "company_domain": person.get("organization", {}).get("primary_domain", ""),
            "linkedin_url": person.get("linkedin_url", ""),
            "phone": person.get("phone", ""),
            "location": f"{person.get('city', '')} {person.get('state', '')}".strip(),
            "department": person.get("department", ""),
            "seniority": person.get("seniority", ""),
            "employment_history": person.get("employment_history", []),
            "education": person.get("education", [])
        }

    async def _search_organizations(self, params: dict[str, Any]) -> ToolResult:
        """Search for organizations"""
        try:
            # Build search parameters
            search_params = {
                "api_key": self.api_key,
                "page": params.get("page", 1),
                "per_page": min(params.get("per_page", 25), 200)
            }

            # Add filters
            if params.get("company_names"):
                search_params["organization_names"] = params["company_names"]
            if params.get("locations"):
                search_params["organization_locations"] = params["locations"]
            if params.get("industries"):
                search_params["organization_industry_tag_ids"] = params["industries"]

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._search_organizations_sync(search_params)
            )

            # Parse results
            org_data = self._parse_organization_search_result(result)

            return self._create_success_result(
                data=org_data,
                metadata={
                    "total_results": result.get("pagination", {}).get("total_entries", 0),
                    "page": search_params["page"],
                    "per_page": search_params["per_page"]
                }
            )

        except Exception as e:
            return self._create_error_result(f"Organization search failed: {e}")

    def _search_organizations_sync(self, search_params: dict[str, Any]) -> dict[str, Any]:
        """Synchronous organization search"""
        url = f"{self.api_base_url}/mixed_companies/search"

        response = self.session.post(url, json=search_params)

        if response.status_code != 200:
            raise Exception(f"Organization search failed: {response.status_code} - {response.text}")

        return response.json()

    def _parse_organization_search_result(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse organization search results"""
        organizations = []

        for org in result.get("organizations", []):
            organizations.append({
                "id": org.get("id", ""),
                "name": org.get("name", ""),
                "domain": org.get("primary_domain", ""),
                "industry": org.get("industry", ""),
                "employee_count": org.get("estimated_num_employees", 0),
                "location": f"{org.get('city', '')} {org.get('state', '')} {org.get('country', '')}".strip(),
                "linkedin_url": org.get("linkedin_url", ""),
                "website": org.get("website", ""),
                "description": org.get("short_description", ""),
                "revenue": org.get("annual_revenue", ""),
                "technologies": [tech.get("name", "") for tech in org.get("technologies", [])]
            })

        return organizations

    def get_mcp_tool_definition(self) -> types.Tool:
        """Return MCP tool definition for Apollo.io"""
        return types.Tool(
            name="apollo",
            description="Apollo.io integration for email finding, contact enrichment, and prospect research with high deliverability",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["find_email", "search_people", "verify_email", "enrich_person", "search_organizations"],
                        "description": "The Apollo.io action to perform"
                    },
                    "first_name": {
                        "type": "string",
                        "description": "First name for email finding"
                    },
                    "last_name": {
                        "type": "string",
                        "description": "Last name for email finding"
                    },
                    "domain": {
                        "type": "string",
                        "description": "Company domain for email finding"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address for verification or enrichment"
                    },
                    "titles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Job titles to search for"
                    },
                    "company_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Company names to search for"
                    },
                    "locations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Geographic locations to search"
                    },
                    "industries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Industries to search for"
                    },
                    "page": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 1,
                        "description": "Page number for pagination"
                    },
                    "per_page": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200,
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
