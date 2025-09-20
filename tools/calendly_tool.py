"""Calendly integration tool for scheduling and managing appointments"""

import asyncio
from typing import Any

import aiohttp
from mcp import types

# Import helper functions for Calendly token refresh
from tools.calendly_helper import _token_manager, get_valid_access_token, initialize_calendly_helper

from .base import SalesTool, ToolResult, validate_required_params


class CalendlyTool(SalesTool):
    """Calendly scheduling operations"""

    def __init__(self):
        super().__init__("calendly", "Calendly scheduling operations for events, invitees, and webhooks")
        self.access_token = None
        self.base_url = "https://api.calendly.com"
        self.user_uri = None
        self.session = None
        self.client_id = None
        self.client_secret = None
        self.refresh_token = None
        self._refresh_task = None

    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Calendly connection and start token refresh background task"""
        # Load credentials from settings
        self.access_token = getattr(settings, "calendly_access_token", None)
        self.client_id = getattr(settings, "calendly_client_id", None)
        self.client_secret = getattr(settings, "calendly_client_secret", None)
        self.refresh_token = getattr(settings, "calendly_refresh_token", None)

        # If using OAuth, refresh access token if needed
        if self.client_id and self.client_secret and self.refresh_token:
            try:
                # Initialize helper and setup token manager
                await initialize_calendly_helper()
                _token_manager.client_id = self.client_id
                _token_manager.client_secret = self.client_secret
                _token_manager.refresh_token = self.refresh_token

                # Get valid access token (will refresh if needed)
                self.access_token = await get_valid_access_token()

                if not self.access_token:
                    self.logger.error("Calendly OAuth token refresh failed at initialization")
                    return False
            except Exception as e:
                self.logger.error(f"Calendly OAuth token refresh failed: {e}")
                return False

        if not self.access_token:
            self.logger.warning("Calendly access token not configured")
            return False

        try:
            # Create HTTP session
            self.session = aiohttp.ClientSession(headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            })

            # Get current user to validate token
            async with self.session.get(f"{self.base_url}/users/me") as resp:
                if resp.status == 200:
                    user_data = await resp.json()
                    self.user_uri = user_data["resource"]["uri"]
                    self.logger.info(f"Calendly authenticated as {user_data['resource']['email']}")
                    # Start background refresh task if using OAuth
                    if self.client_id and self.client_secret and self.refresh_token:
                        self._refresh_task = asyncio.create_task(self._schedule_token_refresh())
                    return True
                error_data = await resp.text()
                self.logger.error(f"Calendly authentication failed: {error_data}")
                return False
        except Exception as e:
            self.logger.error(f"Calendly initialization error: {e}")
            if self.session:
                await self.session.close()
                self.session = None
            return False

    async def _schedule_token_refresh(self):
        """Background task to automatically refresh Calendly access token every ~55 minutes."""
        while True:
            try:
                await asyncio.sleep(55 * 60)  # 55 minutes
                self.logger.info("Refreshing Calendly access token...")

                # Use token manager to ensure valid token
                if await _token_manager.ensure_valid_token():
                    self.access_token = _token_manager.access_token

                    # Update session headers with new token
                    if self.session:
                        self.session._default_headers["Authorization"] = f"Bearer {self.access_token}"

                    self.logger.info("Calendly access token refreshed successfully.")
                else:
                    self.logger.error("Calendly token refresh failed: Unable to ensure valid token.")
            except asyncio.CancelledError:
                self.logger.info("Calendly token refresh task cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Calendly token refresh error: {e}")

    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return self.access_token is not None and self.session is not None

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute Calendly operations"""
        if not self.is_configured():
            return self._create_error_result("Calendly not configured")

        try:
            if action == "get_user":
                return await self._get_user(params)
            if action == "list_event_types":
                return await self._list_event_types(params)
            if action == "get_event_type":
                return await self._get_event_type(params)
            if action == "list_scheduled_events":
                return await self._list_scheduled_events(params)
            if action == "get_scheduled_event":
                return await self._get_scheduled_event(params)
            if action == "cancel_scheduled_event":
                return await self._cancel_scheduled_event(params)
            if action == "list_invitees":
                return await self._list_invitees(params)
            if action == "get_invitee":
                return await self._get_invitee(params)
            if action == "create_webhook":
                return await self._create_webhook(params)
            if action == "list_webhooks":
                return await self._list_webhooks(params)
            if action == "delete_webhook":
                return await self._delete_webhook(params)
            return self._create_error_result(f"Unknown action: {action}")

        except Exception as e:
            self.logger.error(f"Calendly operation failed: {e!s}")
            return self._create_error_result(f"Operation failed: {e!s}")

    async def _get_user(self, params: dict[str, Any]) -> ToolResult:
        """Get current user information"""
        async with self.session.get(f"{self.base_url}/users/me") as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result["resource"])
            error_data = await resp.text()
            return self._create_error_result(f"Failed to get user: {error_data}")

    async def _list_event_types(self, params: dict[str, Any]) -> ToolResult:
        """List available event types"""
        user = params.get("user", self.user_uri)

        async with self.session.get(
            f"{self.base_url}/event_types",
            params={"user": user}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "event_types": result.get("collection", []),
                    "total": len(result.get("collection", []))
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to list event types: {error_data}")

    async def _get_event_type(self, params: dict[str, Any]) -> ToolResult:
        """Get specific event type"""
        error = validate_required_params(params, ["event_type_uuid"])
        if error:
            return self._create_error_result(error)

        event_type_uuid = params["event_type_uuid"]

        async with self.session.get(f"{self.base_url}/event_types/{event_type_uuid}") as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result["resource"])
            error_data = await resp.text()
            return self._create_error_result(f"Failed to get event type: {error_data}")

    async def _list_scheduled_events(self, params: dict[str, Any]) -> ToolResult:
        """List scheduled events"""
        query_params = {
            "user": params.get("user", self.user_uri),
            "count": params.get("count", 20)
        }

        # Add optional filters
        for param in ["status", "min_start_time", "max_start_time", "page_token"]:
            if param in params:
                query_params[param] = params[param]

        async with self.session.get(f"{self.base_url}/scheduled_events", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "events": result.get("collection", []),
                    "pagination": result.get("pagination", {})
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to list events: {error_data}")

    async def _get_scheduled_event(self, params: dict[str, Any]) -> ToolResult:
        """Get specific scheduled event"""
        error = validate_required_params(params, ["event_uuid"])
        if error:
            return self._create_error_result(error)

        event_uuid = params["event_uuid"]

        async with self.session.get(f"{self.base_url}/scheduled_events/{event_uuid}") as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result["resource"])
            error_data = await resp.text()
            return self._create_error_result(f"Failed to get event: {error_data}")

    async def _cancel_scheduled_event(self, params: dict[str, Any]) -> ToolResult:
        """Cancel a scheduled event"""
        error = validate_required_params(params, ["event_uuid"])
        if error:
            return self._create_error_result(error)

        event_uuid = params["event_uuid"]
        reason = params.get("reason", "Canceled by API")

        async with self.session.post(
            f"{self.base_url}/scheduled_events/{event_uuid}/cancellation",
            json={"reason": reason}
        ) as resp:
            if resp.status == 201:
                result = await resp.json()
                return self._create_success_result({
                    "canceled": True,
                    "cancellation": result["resource"]
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to cancel event: {error_data}")

    async def _list_invitees(self, params: dict[str, Any]) -> ToolResult:
        """List invitees for an event"""
        error = validate_required_params(params, ["event_uuid"])
        if error:
            return self._create_error_result(error)

        event_uuid = params["event_uuid"]
        query_params = {"count": params.get("count", 20)}

        # Add optional filters
        for param in ["email", "status", "page_token"]:
            if param in params:
                query_params[param] = params[param]

        async with self.session.get(
            f"{self.base_url}/scheduled_events/{event_uuid}/invitees",
            params=query_params
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "invitees": result.get("collection", []),
                    "pagination": result.get("pagination", {})
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to list invitees: {error_data}")

    async def _get_invitee(self, params: dict[str, Any]) -> ToolResult:
        """Get specific invitee"""
        error = validate_required_params(params, ["event_uuid", "invitee_uuid"])
        if error:
            return self._create_error_result(error)

        event_uuid = params["event_uuid"]
        invitee_uuid = params["invitee_uuid"]

        url = f"{self.base_url}/scheduled_events/{event_uuid}/invitees/{invitee_uuid}"

        async with self.session.get(url) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result(result["resource"])
            return self._create_error_result(f"Invitee not found: {invitee_uuid}")

    async def _create_webhook(self, params: dict[str, Any]) -> ToolResult:
        """Create webhook subscription"""
        error = validate_required_params(params, ["url", "events"])
        if error:
            return self._create_error_result(error)

        data = {
            "url": params["url"],
            "events": params["events"],
            "organization": params.get("organization"),
            "user": params.get("user"),
            "scope": params.get("scope", "user")
        }

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        async with self.session.post(f"{self.base_url}/webhook_subscriptions", json=data) as resp:
            if resp.status == 201:
                result = await resp.json()
                return self._create_success_result({
                    "webhook_uuid": result["resource"]["uri"].split("/")[-1],
                    "webhook": result["resource"],
                    "created": True
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to create webhook: {error_data}")

    async def _list_webhooks(self, params: dict[str, Any]) -> ToolResult:
        """List webhook subscriptions"""
        organization_uri = params.get("organization")
        user_uri = params.get("user", self.user_uri)
        scope = params.get("scope", "user")

        query_params = {"scope": scope}

        if organization_uri:
            query_params["organization"] = organization_uri
        if user_uri:
            query_params["user"] = user_uri

        async with self.session.get(f"{self.base_url}/webhook_subscriptions", params=query_params) as resp:
            if resp.status == 200:
                result = await resp.json()
                return self._create_success_result({
                    "webhooks": result.get("collection", []),
                    "total": len(result.get("collection", []))
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to list webhooks: {error_data}")

    async def _delete_webhook(self, params: dict[str, Any]) -> ToolResult:
        """Delete webhook subscription"""
        error = validate_required_params(params, ["webhook_uuid"])
        if error:
            return self._create_error_result(error)

        webhook_uuid = params["webhook_uuid"]

        async with self.session.delete(f"{self.base_url}/webhook_subscriptions/{webhook_uuid}") as resp:
            if resp.status == 204:
                return self._create_success_result({
                    "deleted": True,
                    "webhook_uuid": webhook_uuid
                })
            error_data = await resp.text()
            return self._create_error_result(f"Failed to delete webhook: {error_data}")

    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition"""
        return types.Tool(
            name="calendly",
            description="Calendly scheduling operations for events, invitees, and webhooks",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "get_user", "list_event_types", "get_event_type",
                            "list_scheduled_events", "get_scheduled_event", "cancel_scheduled_event",
                            "list_invitees", "get_invitee",
                            "create_webhook", "list_webhooks", "delete_webhook"
                        ],
                        "description": "The action to perform"
                    },
                    "event_type_uuid": {"type": "string", "description": "Event type UUID"},
                    "event_uuid": {"type": "string", "description": "Scheduled event UUID"},
                    "invitee_uuid": {"type": "string", "description": "Invitee UUID"},
                    "webhook_uuid": {"type": "string", "description": "Webhook UUID"},
                    "user": {"type": "string", "description": "User URI"},
                    "organization": {"type": "string", "description": "Organization URI"},
                    "url": {"type": "string", "description": "Webhook URL"},
                    "events": {"type": "array", "items": {"type": "string"}, "description": "Webhook events"},
                    "scope": {"type": "string", "enum": ["user", "organization"], "description": "Webhook scope"},
                    "status": {"type": "string", "description": "Event status filter"},
                    "reason": {"type": "string", "description": "Cancellation reason"},
                    "email": {"type": "string", "description": "Invitee email filter"},
                    "min_start_time": {"type": "string", "description": "Minimum start time (ISO 8601)"},
                    "max_start_time": {"type": "string", "description": "Maximum start time (ISO 8601)"},
                    "count": {"type": "integer", "description": "Results count", "default": 20},
                    "page_token": {"type": "string", "description": "Pagination token"},
                    "sort": {"type": "string", "description": "Sort order"}
                },
                "required": ["action"]
            }
        )

    async def cleanup(self):
        """Clean up resources and cancel token refresh task"""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        if self.session:
            await self.session.close()
        self.logger.info("Calendly tool cleaned up")
