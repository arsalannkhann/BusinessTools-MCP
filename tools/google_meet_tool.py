"""
Google Meet integration tool
Handles meeting creation and management through Google Calendar
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from mcp import types

from .base import SalesTool, ToolResult, validate_required_params


class GoogleMeetTool(SalesTool):
    """Google Meet operations through Google Calendar"""

    def __init__(self):
        super().__init__("google_meet", "Google Meet integration for video meetings")
        self.google_auth = None
        self.calendar_service = None

    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Google Meet connection via Calendar API"""
        if not google_auth or not google_auth.is_authenticated():
            self.logger.warning("Google authentication not available")
            return False

        self.google_auth = google_auth

        try:
            self.calendar_service = google_auth.get_service("calendar")

            # Test connection
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.calendar_service.calendarList().list(maxResults=1).execute()
            )

            self.logger.info("Google Meet connection validated")
            return True

        except Exception as e:
            self.logger.error(f"Google Meet initialization failed: {e}")
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute Google Meet operations"""
        if not self.calendar_service:
            return self._create_error_result("Google Meet not initialized")

        try:
            if action == "create_meeting":
                return await self._create_meeting(params)
            if action == "create_instant_meeting":
                return await self._create_instant_meeting(params)
            if action == "get_meeting":
                return await self._get_meeting(params)
            if action == "update_meeting":
                return await self._update_meeting(params)
            if action == "end_meeting":
                return await self._end_meeting(params)
            return self._create_error_result(f"Unknown action: {action}")

        except Exception as e:
            return self._create_error_result(f"Google Meet operation failed: {e!s}")

    async def _create_meeting(self, params: dict[str, Any]) -> ToolResult:
        """Create a scheduled Google Meet meeting"""
        error = validate_required_params(params, ["title", "start_time", "duration_minutes"])
        if error:
            return self._create_error_result(error)

        title = params["title"]
        start_time = params["start_time"]
        duration_minutes = params["duration_minutes"]
        description = params.get("description", "")
        attendees = params.get("attendees", [])
        calendar_id = params.get("calendar_id", "primary")

        # Parse start time
        if isinstance(start_time, str):
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        else:
            start_dt = start_time

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        # Create event with Google Meet
        event = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": params.get("timezone", "UTC")
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": params.get("timezone", "UTC")
            },
            "conferenceData": {
                "createRequest": {
                    "requestId": f"meet-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        }

        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        loop = asyncio.get_event_loop()

        try:
            created_event = await loop.run_in_executor(
                None,
                lambda: self.calendar_service.events().insert(
                    calendarId=calendar_id,
                    body=event,
                    conferenceDataVersion=1
                ).execute()
            )

            # Extract Google Meet info
            meet_link = None
            if "conferenceData" in created_event:
                meet_info = created_event["conferenceData"]
                if "entryPoints" in meet_info:
                    for entry in meet_info["entryPoints"]:
                        if entry["entryPointType"] == "video":
                            meet_link = entry["uri"]
                            break

            return self._create_success_result({
                "meeting_id": created_event["id"],
                "event_id": created_event["id"],
                "title": created_event["summary"],
                "start_time": created_event["start"]["dateTime"],
                "end_time": created_event["end"]["dateTime"],
                "google_meet_link": meet_link,
                "html_link": created_event.get("htmlLink", ""),
                "created": True
            })

        except Exception as e:
            return self._create_error_result(f"Failed to create Google Meet meeting: {e!s}")

    async def _create_instant_meeting(self, params: dict[str, Any]) -> ToolResult:
        """Create an instant Google Meet meeting"""
        title = params.get("title", "Instant Meeting")
        description = params.get("description", "Instant Google Meet")
        duration_minutes = params.get("duration_minutes", 60)
        calendar_id = params.get("calendar_id", "primary")

        # Create event starting now
        start_dt = datetime.now()
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "UTC"
            },
            "conferenceData": {
                "createRequest": {
                    "requestId": f"instant-meet-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        }

        loop = asyncio.get_event_loop()

        try:
            created_event = await loop.run_in_executor(
                None,
                lambda: self.calendar_service.events().insert(
                    calendarId=calendar_id,
                    body=event,
                    conferenceDataVersion=1
                ).execute()
            )

            # Extract Google Meet info
            meet_link = None
            if "conferenceData" in created_event:
                meet_info = created_event["conferenceData"]
                if "entryPoints" in meet_info:
                    for entry in meet_info["entryPoints"]:
                        if entry["entryPointType"] == "video":
                            meet_link = entry["uri"]
                            break

            return self._create_success_result({
                "meeting_id": created_event["id"],
                "title": created_event["summary"],
                "google_meet_link": meet_link,
                "start_time": created_event["start"]["dateTime"],
                "end_time": created_event["end"]["dateTime"],
                "instant": True,
                "created": True
            })

        except Exception as e:
            return self._create_error_result(f"Failed to create instant meeting: {e!s}")

    async def _get_meeting(self, params: dict[str, Any]) -> ToolResult:
        """Get meeting details by event ID"""
        error = validate_required_params(params, ["meeting_id"])
        if error:
            return self._create_error_result(error)

        meeting_id = params["meeting_id"]
        calendar_id = params.get("calendar_id", "primary")

        loop = asyncio.get_event_loop()

        try:
            event = await loop.run_in_executor(
                None,
                lambda: self.calendar_service.events().get(
                    calendarId=calendar_id,
                    eventId=meeting_id
                ).execute()
            )

            # Extract Google Meet info
            meet_link = None
            if "conferenceData" in event:
                meet_info = event["conferenceData"]
                if "entryPoints" in meet_info:
                    for entry in meet_info["entryPoints"]:
                        if entry["entryPointType"] == "video":
                            meet_link = entry["uri"]
                            break

            return self._create_success_result({
                "meeting_id": event["id"],
                "title": event.get("summary", ""),
                "description": event.get("description", ""),
                "start_time": event.get("start", {}).get("dateTime", ""),
                "end_time": event.get("end", {}).get("dateTime", ""),
                "google_meet_link": meet_link,
                "status": event.get("status", ""),
                "attendees": event.get("attendees", []),
                "html_link": event.get("htmlLink", "")
            })

        except Exception as e:
            return self._create_error_result(f"Failed to get meeting: {e!s}")

    async def _update_meeting(self, params: dict[str, Any]) -> ToolResult:
        """Update meeting details"""
        error = validate_required_params(params, ["meeting_id"])
        if error:
            return self._create_error_result(error)

        meeting_id = params["meeting_id"]
        calendar_id = params.get("calendar_id", "primary")

        loop = asyncio.get_event_loop()

        try:
            # Get existing event
            existing_event = await loop.run_in_executor(
                None,
                lambda: self.calendar_service.events().get(
                    calendarId=calendar_id,
                    eventId=meeting_id
                ).execute()
            )

            # Update fields
            if "title" in params:
                existing_event["summary"] = params["title"]
            if "description" in params:
                existing_event["description"] = params["description"]
            if "start_time" in params:
                start_dt = datetime.fromisoformat(params["start_time"].replace("Z", "+00:00"))
                existing_event["start"] = {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": params.get("timezone", "UTC")
                }
            if "end_time" in params:
                end_dt = datetime.fromisoformat(params["end_time"].replace("Z", "+00:00"))
                existing_event["end"] = {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": params.get("timezone", "UTC")
                }
            if "attendees" in params:
                existing_event["attendees"] = [{"email": email} for email in params["attendees"]]

            # Update the event
            updated_event = await loop.run_in_executor(
                None,
                lambda: self.calendar_service.events().update(
                    calendarId=calendar_id,
                    eventId=meeting_id,
                    body=existing_event
                ).execute()
            )

            return self._create_success_result({
                "meeting_id": updated_event["id"],
                "updated": True,
                "title": updated_event.get("summary", ""),
                "start_time": updated_event.get("start", {}).get("dateTime", ""),
                "end_time": updated_event.get("end", {}).get("dateTime", "")
            })

        except Exception as e:
            return self._create_error_result(f"Failed to update meeting: {e!s}")

    async def _end_meeting(self, params: dict[str, Any]) -> ToolResult:
        """End a meeting by updating its end time to now"""
        error = validate_required_params(params, ["meeting_id"])
        if error:
            return self._create_error_result(error)

        meeting_id = params["meeting_id"]
        calendar_id = params.get("calendar_id", "primary")

        loop = asyncio.get_event_loop()

        try:
            # Get existing event
            existing_event = await loop.run_in_executor(
                None,
                lambda: self.calendar_service.events().get(
                    calendarId=calendar_id,
                    eventId=meeting_id
                ).execute()
            )

            # Set end time to now
            now = datetime.now()
            existing_event["end"] = {
                "dateTime": now.isoformat(),
                "timeZone": "UTC"
            }

            # Update the event
            updated_event = await loop.run_in_executor(
                None,
                lambda: self.calendar_service.events().update(
                    calendarId=calendar_id,
                    eventId=meeting_id,
                    body=existing_event
                ).execute()
            )

            return self._create_success_result({
                "meeting_id": updated_event["id"],
                "ended": True,
                "end_time": updated_event.get("end", {}).get("dateTime", "")
            })

        except Exception as e:
            return self._create_error_result(f"Failed to end meeting: {e!s}")

    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition"""
        return types.Tool(
            name="google_meet",
            description="Google Meet video meeting operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create_meeting", "create_instant_meeting", "get_meeting", "update_meeting", "end_meeting"],
                        "description": "The action to perform"
                    },
                    "meeting_id": {"type": "string", "description": "Meeting/Event ID"},
                    "calendar_id": {"type": "string", "description": "Calendar ID (default: primary)"},
                    "title": {"type": "string", "description": "Meeting title"},
                    "description": {"type": "string", "description": "Meeting description"},
                    "start_time": {"type": "string", "description": "Meeting start time (ISO 8601)"},
                    "end_time": {"type": "string", "description": "Meeting end time (ISO 8601)"},
                    "duration_minutes": {"type": "integer", "description": "Meeting duration in minutes"},
                    "timezone": {"type": "string", "description": "Timezone", "default": "UTC"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "Attendee emails"}
                },
                "required": ["action"]
            }
        )

    async def cleanup(self):
        """Clean up resources"""
        self.logger.info("Google Meet tool cleaned up")
