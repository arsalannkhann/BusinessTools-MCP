"""
LinkedIn Sales Navigator integration tool
Handles LinkedIn prospecting, profile research, and outreach
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
from mcp import types

from .base import SalesTool, ToolResult, validate_required_params


@dataclass
class LinkedInProfile:
    """LinkedIn profile data structure"""
    linkedin_id: str
    name: str
    headline: str
    current_company: str
    current_position: str
    location: str
    profile_url: str
    connections: int = 0
    industry: str = ""
    summary: str = ""
    experience: list[dict[str, Any]] | None = None
    education: list[dict[str, Any]] | None = None
    skills: list[str] | None = None

    def __post_init__(self):
        if self.experience is None:
            self.experience = []
        if self.education is None:
            self.education = []
        if self.skills is None:
            self.skills = []


class LinkedInSalesNavigatorTool(SalesTool):
    """LinkedIn Sales Navigator operations for prospecting and outreach"""

    def __init__(self):
        super().__init__("linkedin_sales_navigator", "LinkedIn Sales Navigator integration for prospecting and outreach")
        self.access_token = None
        self.api_base_url = "https://api.linkedin.com/v2"
        self.sales_navigator_url = "https://www.linkedin.com/sales/api"
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.rate_limit_delay = 1.0  # Delay between requests to respect rate limits
        self.session = None

    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize LinkedIn Sales Navigator connection"""
        try:
            # Get LinkedIn credentials from settings
            self.access_token = getattr(settings, "linkedin_access_token", None)
            self.client_id = getattr(settings, "linkedin_client_id", None)
            self.client_secret = getattr(settings, "linkedin_client_secret", None)

            if not self.access_token:
                self.logger.warning("LinkedIn access token not configured")
                return False

            # Initialize HTTP session
            self.session = requests.Session()
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            })

            # Test the connection
            await self._test_connection()

            self.logger.info("LinkedIn Sales Navigator API connection validated")
            return True

        except Exception as e:
            self.logger.error(f"LinkedIn Sales Navigator initialization failed: {e}")
            return False

    async def _test_connection(self):
        """Test LinkedIn API connection"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._test_connection_sync
        )

    def _test_connection_sync(self):
        """Synchronous connection test"""
        response = self.session.get(f"{self.api_base_url}/people/~")
        if response.status_code != 200:
            raise Exception(f"LinkedIn API test failed: {response.status_code} - {response.text}")

    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return bool(self.access_token and self.session)

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute LinkedIn Sales Navigator operations"""
        try:
            if action == "search_profiles":
                return await self._search_profiles(params)
            if action == "get_profile":
                return await self._get_profile(params)
            if action == "send_connection_request":
                return await self._send_connection_request(params)
            if action == "send_message":
                return await self._send_message(params)
            if action == "get_company_employees":
                return await self._get_company_employees(params)
            if action == "track_profile_engagement":
                return await self._track_profile_engagement(params)
            if action == "save_lead":
                return await self._save_lead(params)
            if action == "get_lead_recommendations":
                return await self._get_lead_recommendations(params)
            return self._create_error_result(f"Unknown action: {action}")

        except Exception as e:
            return self._create_error_result(f"LinkedIn operation failed: {e!s}")

    async def _search_profiles(self, params: dict[str, Any]) -> ToolResult:
        """Search for LinkedIn profiles with various filters"""
        validation_error = validate_required_params(params, ["query"])
        if validation_error:
            return self._create_error_result(validation_error)

        query = params["query"]
        filters = {
            "keywords": query,
            "start": params.get("start", 0),
            "count": min(params.get("count", 25), 50),  # LinkedIn limits to 50
            "facets": []
        }

        # Add location filter
        if params.get("location"):
            filters["facets"].append(f"geoRegion,{params['location']}")

        # Add current company filter
        if params.get("current_company"):
            filters["facets"].append(f"currentCompany,{params['current_company']}")

        # Add industry filter
        if params.get("industry"):
            filters["facets"].append(f"industry,{params['industry']}")

        # Add experience level filter
        if params.get("seniority_level"):
            filters["facets"].append(f"seniorityLevel,{params['seniority_level']}")

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._search_profiles_sync(filters)
            )

            # Parse and format results
            profiles = self._parse_profile_search_results(result)

            return self._create_success_result(
                data=profiles,
                metadata={
                    "query": query,
                    "total_results": len(profiles),
                    "filters_applied": list(filters.keys())
                }
            )

        except Exception as e:
            return self._create_error_result(f"Profile search failed: {e}")

    def _search_profiles_sync(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Synchronous profile search"""
        # Build facets parameter
        facets_param = ",".join(filters.get("facets", []))

        params = {
            "keywords": filters["keywords"],
            "start": filters["start"],
            "count": filters["count"]
        }

        if facets_param:
            params["facets"] = facets_param

        # Use people search endpoint
        url = f"{self.api_base_url}/peopleSearch?" + urlencode(params)

        response = self.session.get(url)
        time.sleep(self.rate_limit_delay)  # Rate limiting

        if response.status_code != 200:
            raise Exception(f"Profile search failed: {response.status_code} - {response.text}")

        return response.json()

    def _parse_profile_search_results(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse LinkedIn profile search results"""
        profiles = []

        elements = result.get("elements", [])
        for element in elements:
            profile_data = {
                "linkedin_id": element.get("targetUrn", "").replace("urn:li:fsd_profile:", ""),
                "name": self._get_localized_text(element.get("title", {})),
                "headline": self._get_localized_text(element.get("headline", {})),
                "location": self._get_localized_text(element.get("subline", {})),
                "profile_url": f"https://linkedin.com/in/{element.get('publicIdentifier', '')}",
                "image_url": element.get("image", {}).get("rootUrl", ""),
                "industry": element.get("industry", ""),
                "current_position": "",
                "current_company": ""
            }

            # Extract current position and company from snippet
            snippet = element.get("snippet", {})
            if snippet:
                profile_data["current_position"] = snippet.get("title", "")
                profile_data["current_company"] = snippet.get("company", "")

            profiles.append(profile_data)

        return profiles

    def _get_localized_text(self, text_obj: dict[str, Any]) -> str:
        """Extract localized text from LinkedIn API response"""
        if isinstance(text_obj, dict):
            return text_obj.get("text", "") or text_obj.get("localized", {}).get("en_US", "")
        return str(text_obj) if text_obj else ""

    async def _get_profile(self, params: dict[str, Any]) -> ToolResult:
        """Get detailed profile information"""
        validation_error = validate_required_params(params, ["profile_id"])
        if validation_error:
            return self._create_error_result(validation_error)

        profile_id = params["profile_id"]

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._get_profile_sync(profile_id)
            )

            # Parse detailed profile
            profile = self._parse_detailed_profile(result)

            return self._create_success_result(
                data=profile,
                metadata={"profile_id": profile_id}
            )

        except Exception as e:
            return self._create_error_result(f"Profile fetch failed: {e}")

    def _get_profile_sync(self, profile_id: str) -> dict[str, Any]:
        """Synchronous profile fetch"""
        url = f"{self.api_base_url}/people/id={profile_id}"

        response = self.session.get(url)
        time.sleep(self.rate_limit_delay)

        if response.status_code != 200:
            raise Exception(f"Profile fetch failed: {response.status_code} - {response.text}")

        return response.json()

    def _parse_detailed_profile(self, result: dict[str, Any]) -> dict[str, Any]:
        """Parse detailed LinkedIn profile"""
        return {
            "linkedin_id": result.get("id", ""),
            "name": f"{result.get('firstName', '')} {result.get('lastName', '')}".strip(),
            "headline": result.get("headline", ""),
            "location": result.get("location", {}).get("name", ""),
            "industry": result.get("industry", ""),
            "summary": result.get("summary", ""),
            "profile_url": result.get("publicProfileUrl", ""),
            "connections": result.get("numConnections", 0),
            "profile_picture": result.get("profilePicture", {}).get("displayImage", "")
        }

    async def _send_connection_request(self, params: dict[str, Any]) -> ToolResult:
        """Send connection request to a LinkedIn profile"""
        validation_error = validate_required_params(params, ["profile_id"])
        if validation_error:
            return self._create_error_result(validation_error)

        profile_id = params["profile_id"]
        message = params.get("message", "")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self._send_connection_request_sync(profile_id, message)
            )

            return self._create_success_result(
                data={"status": "connection_request_sent"},
                metadata={
                    "profile_id": profile_id,
                    "message_included": bool(message)
                }
            )

        except Exception as e:
            return self._create_error_result(f"Connection request failed: {e}")

    def _send_connection_request_sync(self, profile_id: str, message: str) -> dict[str, Any]:
        """Synchronous connection request"""
        url = f"{self.api_base_url}/invitations"

        payload = {
            "inviteType": "CONNECT_TO_PERSON",
            "targetUrn": f"urn:li:person:{profile_id}",
            "message": message
        }

        response = self.session.post(url, json=payload)
        time.sleep(self.rate_limit_delay)

        if response.status_code not in [200, 201]:
            raise Exception(f"Connection request failed: {response.status_code} - {response.text}")

        return response.json() if response.content else {"status": "sent"}

    async def _send_message(self, params: dict[str, Any]) -> ToolResult:
        """Send a direct message to a LinkedIn connection"""
        validation_error = validate_required_params(params, ["profile_id", "message"])
        if validation_error:
            return self._create_error_result(validation_error)

        profile_id = params["profile_id"]
        message = params["message"]
        subject = params.get("subject", "Message from Sales Team")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self._send_message_sync(profile_id, message, subject)
            )

            return self._create_success_result(
                data={"status": "message_sent"},
                metadata={
                    "profile_id": profile_id,
                    "message_length": len(message)
                }
            )

        except Exception as e:
            return self._create_error_result(f"Message sending failed: {e}")

    def _send_message_sync(self, profile_id: str, message: str, subject: str) -> dict[str, Any]:
        """Synchronous message sending"""
        url = f"{self.api_base_url}/messages"

        payload = {
            "recipients": [f"urn:li:person:{profile_id}"],
            "subject": subject,
            "body": message
        }

        response = self.session.post(url, json=payload)
        time.sleep(self.rate_limit_delay)

        if response.status_code not in [200, 201]:
            raise Exception(f"Message sending failed: {response.status_code} - {response.text}")

        return response.json() if response.content else {"status": "sent"}

    async def _get_company_employees(self, params: dict[str, Any]) -> ToolResult:
        """Get employees of a specific company"""
        validation_error = validate_required_params(params, ["company_name"])
        if validation_error:
            return self._create_error_result(validation_error)

        company_name = params["company_name"]
        count = min(params.get("count", 25), 50)
        seniority_level = params.get("seniority_level", "")
        department = params.get("department", "")

        try:
            # Search for profiles with company filter
            search_params = {
                "query": f'company:"{company_name}"',
                "count": count,
                "current_company": company_name
            }

            if seniority_level:
                search_params["seniority_level"] = seniority_level

            result = await self._search_profiles(search_params)

            if result.success:
                # Filter and enhance results
                employees = result.data
                for employee in employees:
                    employee["company_searched"] = company_name
                    employee["search_type"] = "company_employees"

                return self._create_success_result(
                    data=employees,
                    metadata={
                        "company_name": company_name,
                        "employee_count": len(employees),
                        "filters": {
                            "seniority_level": seniority_level,
                            "department": department
                        }
                    }
                )
            return result

        except Exception as e:
            return self._create_error_result(f"Company employee search failed: {e}")

    async def _track_profile_engagement(self, params: dict[str, Any]) -> ToolResult:
        """Track engagement with a LinkedIn profile"""
        validation_error = validate_required_params(params, ["profile_id"])
        if validation_error:
            return self._create_error_result(validation_error)

        profile_id = params["profile_id"]
        engagement_type = params.get("engagement_type", "profile_view")  # profile_view, post_like, post_comment

        try:
            # For demo purposes, we'll simulate engagement tracking
            # In a real implementation, this would integrate with LinkedIn's tracking APIs
            engagement_data = {
                "profile_id": profile_id,
                "engagement_type": engagement_type,
                "timestamp": time.time(),
                "status": "tracked"
            }

            return self._create_success_result(
                data=engagement_data,
                metadata={"tracking_enabled": True}
            )

        except Exception as e:
            return self._create_error_result(f"Engagement tracking failed: {e}")

    async def _save_lead(self, params: dict[str, Any]) -> ToolResult:
        """Save a LinkedIn profile as a lead"""
        validation_error = validate_required_params(params, ["profile_id"])
        if validation_error:
            return self._create_error_result(validation_error)

        profile_id = params["profile_id"]
        notes = params.get("notes", "")
        tags = params.get("tags", [])
        priority = params.get("priority", "medium")  # low, medium, high

        try:
            # First get the profile details
            profile_result = await self._get_profile({"profile_id": profile_id})

            if not profile_result.success:
                return profile_result

            lead_data = {
                "profile": profile_result.data,
                "notes": notes,
                "tags": tags,
                "priority": priority,
                "saved_at": time.time(),
                "status": "new_lead"
            }

            return self._create_success_result(
                data=lead_data,
                metadata={"lead_saved": True, "profile_id": profile_id}
            )

        except Exception as e:
            return self._create_error_result(f"Lead saving failed: {e}")

    async def _get_lead_recommendations(self, params: dict[str, Any]) -> ToolResult:
        """Get LinkedIn lead recommendations based on current network and interests"""
        try:
            industry = params.get("industry", "")
            location = params.get("location", "")
            seniority_level = params.get("seniority_level", "")
            count = min(params.get("count", 10), 25)

            # Build search query for recommendations
            search_params = {
                "query": "decision maker OR director OR manager OR VP OR CEO",
                "count": count
            }

            if industry:
                search_params["industry"] = industry
            if location:
                search_params["location"] = location
            if seniority_level:
                search_params["seniority_level"] = seniority_level

            result = await self._search_profiles(search_params)

            if result.success:
                recommendations = result.data
                for rec in recommendations:
                    rec["recommendation_score"] = self._calculate_recommendation_score(rec)
                    rec["reason"] = "Based on industry and seniority level match"

                # Sort by recommendation score
                recommendations.sort(key=lambda x: x.get("recommendation_score", 0), reverse=True)

                return self._create_success_result(
                    data=recommendations,
                    metadata={
                        "recommendation_criteria": search_params,
                        "total_recommendations": len(recommendations)
                    }
                )
            return result

        except Exception as e:
            return self._create_error_result(f"Lead recommendations failed: {e}")

    def _calculate_recommendation_score(self, profile: dict[str, Any]) -> float:
        """Calculate recommendation score for a profile"""
        score = 0.0

        # Score based on headline keywords
        headline = profile.get("headline", "").lower()
        high_value_keywords = ["ceo", "cto", "vp", "director", "head", "manager", "lead"]
        for keyword in high_value_keywords:
            if keyword in headline:
                score += 1.0

        # Score based on company presence
        if profile.get("current_company"):
            score += 0.5

        # Score based on location (higher for major business centers)
        location = profile.get("location", "").lower()
        major_cities = ["new york", "san francisco", "london", "paris", "toronto", "sydney"]
        for city in major_cities:
            if city in location:
                score += 0.3
                break

        return score

    def get_mcp_tool_definition(self) -> types.Tool:
        """Return MCP tool definition for LinkedIn Sales Navigator"""
        return types.Tool(
            name="linkedin_sales_navigator",
            description="LinkedIn Sales Navigator integration for prospecting, profile research, and outreach automation",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "search_profiles", "get_profile", "send_connection_request",
                            "send_message", "get_company_employees", "track_profile_engagement",
                            "save_lead", "get_lead_recommendations"
                        ],
                        "description": "The LinkedIn action to perform"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query for profile search"
                    },
                    "profile_id": {
                        "type": "string",
                        "description": "LinkedIn profile ID for profile-specific actions"
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Company name for employee search"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message content for connection requests or direct messages"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject line for messages"
                    },
                    "location": {
                        "type": "string",
                        "description": "Geographic location filter"
                    },
                    "industry": {
                        "type": "string",
                        "description": "Industry filter"
                    },
                    "seniority_level": {
                        "type": "string",
                        "enum": ["entry", "associate", "mid-senior", "director", "executive"],
                        "description": "Seniority level filter"
                    },
                    "department": {
                        "type": "string",
                        "description": "Department/function filter"
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 25,
                        "description": "Number of results to return"
                    },
                    "start": {
                        "type": "integer",
                        "minimum": 0,
                        "default": 0,
                        "description": "Starting index for pagination"
                    },
                    "engagement_type": {
                        "type": "string",
                        "enum": ["profile_view", "post_like", "post_comment", "message_sent"],
                        "default": "profile_view",
                        "description": "Type of engagement to track"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes to add when saving a lead"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to add when saving a lead"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "default": "medium",
                        "description": "Priority level for saved leads"
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
