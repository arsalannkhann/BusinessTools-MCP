"""Googleclass GoogleCalendarTool(SalesTool):Calendar integration tool for managing calendar events"""

import logging
import datetime
from typing import Dict, Any, Optional, List

import mcp.types as types
from .base import SalesTool, ToolResult, validate_required_params

class GoogleCalendarTool(SalesToool):
    """Google Calendar operations"""
    
    def __init__(self):
        super().__init__("google_calendar", "Google Calendar operations for events and scheduling")
        self.calendar_service = None
        self.google_auth = None
        self.default_calendar_id = "primary"
    
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Google Calendar connection"""
        if not google_auth or not google_auth.is_authenticated():
            self.logger.warning("Google authentication not available")
            return False
        
        try:
            # Store google_auth reference for automatic refresh
            self.google_auth = google_auth
            
            self.calendar_service = google_auth.get_service('calendar')
            if not self.calendar_service:
                self.logger.error("Failed to get Google Calendar service")
                return False
            
            # Set default calendar ID from settings if available
            if hasattr(settings, "google_default_calendar_id") and settings.google_default_calendar_id:
                self.default_calendar_id = settings.google_default_calendar_id
            
            self.logger.info("Google Calendar tool initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Google Calendar initialization error: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return self.calendar_service is not None
    
    async def _ensure_fresh_service(self):
        """Ensure service has fresh credentials (for production)"""
        if self.google_auth:
            try:
                # This will refresh credentials if needed
                await self.google_auth.ensure_valid_credentials()
                
                # Get fresh service if credentials were refreshed
                fresh_service = self.google_auth.get_service('calendar')
                if fresh_service:
                    self.calendar_service = fresh_service
                    
            except Exception as e:
                self.logger.warning(f"Could not refresh calendar service: {e}")
    
    async def execute(self, action: str, params: Dict[str, Any]) -> ToolResult:
        """Execute Google Calendar operations"""
        if not self.is_configured():
            return self._create_error_result("Google Calendar not configured")
        
        # Ensure fresh credentials for production
        await self._ensure_fresh_service()
        
        try:
            if action == "list_calendars":
                return await self._list_calendars(params)
            elif action == "get_calendar":
                return await self._get_calendar(params)
            elif action == "list_events":
                return await self._list_events(params)
            elif action == "get_event":
                return await self._get_event(params)
            elif action == "create_event":
                return await self._create_event(params)
            elif action == "update_event":
                return await self._update_event(params)
            elif action == "delete_event":
                return await self._delete_event(params)
            elif action == "check_availability":
                return await self._check_availability(params)
            else:
                return self._create_error_result(f"Unknown action: {action}")
        
        except Exception as e:
            self.logger.error(f"Google Calendar operation failed: {str(e)}")
            return self._create_error_result(f"Operation failed: {str(e)}")
    
    async def _list_calendars(self, params: Dict[str, Any]) -> ToolResult:
        """List available calendars"""
        try:
            # Execute the API request synchronously since Google API client is not async
            result = self.calendar_service.calendarList().list().execute()
            
            calendars = result.get("items", [])
            return self._create_success_result({
                "calendars": calendars,
                "total": len(calendars)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to list calendars: {str(e)}")
    
    async def _get_calendar(self, params: Dict[str, Any]) -> ToolResult:
        """Get specific calendar"""
        error = validate_required_params(params, ["calendar_id"])
        if error:
            return self._create_error_result(error)
        
        calendar_id = params["calendar_id"]
        
        try:
            calendar = self.calendar_service.calendars().get(calendarId=calendar_id).execute()
            return self._create_success_result(calendar)
            
        except Exception as e:
            return self._create_error_result(f"Failed to get calendar: {str(e)}")
    
    async def _list_events(self, params: Dict[str, Any]) -> ToolResult:
        """List calendar events"""
        calendar_id = params.get("calendar_id", self.default_calendar_id)
        
        # Build request parameters
        request_params = {}
        
        # Add optional filters
        for param_name, api_param in [
            ("max_results", "maxResults"),
            ("time_min", "timeMin"),
            ("time_max", "timeMax"),
            ("q", "q"),
            ("single_events", "singleEvents"),
            ("order_by", "orderBy"),
            ("page_token", "pageToken")
        ]:
            if param_name in params:
                request_params[api_param] = params[param_name]
        
        try:
            result = self.calendar_service.events().list(
                calendarId=calendar_id, **request_params
            ).execute()
            
            return self._create_success_result({
                "events": result.get("items", []),
                "next_page_token": result.get("nextPageToken"),
                "total": len(result.get("items", []))
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to list events: {str(e)}")
    
    async def _get_event(self, params: Dict[str, Any]) -> ToolResult:
        """Get specific event"""
        error = validate_required_params(params, ["event_id"])
        if error:
            return self._create_error_result(error)
        
        event_id = params["event_id"]
        calendar_id = params.get("calendar_id", self.default_calendar_id)
        
        try:
            event = self.calendar_service.events().get(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            
            return self._create_success_result(event)
            
        except Exception as e:
            return self._create_error_result(f"Failed to get event: {str(e)}")
    
    async def _create_event(self, params: Dict[str, Any]) -> ToolResult:
        """Create calendar event"""
        error = validate_required_params(params, ["summary"])
        if error:
            return self._create_error_result(error)
        
        calendar_id = params.get("calendar_id", self.default_calendar_id)
        
        # Build event data
        event_data = {
            "summary": params["summary"],
            "description": params.get("description", ""),
            "location": params.get("location", "")
        }
        
        # Handle start and end times
        if "start_time" in params and "end_time" in params:
            # ISO format datetime strings
            event_data["start"] = {"dateTime": params["start_time"]}
            event_data["end"] = {"dateTime": params["end_time"]}
        elif "start_date" in params and "end_date" in params:
            # All-day event
            event_data["start"] = {"date": params["start_date"]}
            event_data["end"] = {"date": params["end_date"]}
        else:
            return self._create_error_result("Either start_time/end_time or start_date/end_date required")
        
        # Handle attendees
        if "attendees" in params:
            event_data["attendees"] = [
                {"email": email} for email in params["attendees"]
            ]
        
        # Handle reminders
        if "reminders" in params:
            event_data["reminders"] = params["reminders"]
        
        # Handle recurrence
        if "recurrence" in params:
            event_data["recurrence"] = params["recurrence"]
        
        # Handle conference data
        if params.get("add_conference", False):
            event_data["conferenceData"] = {
                "createRequest": {
                    "requestId": f"meeting-{datetime.datetime.now().timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        
        try:
            created_event = self.calendar_service.events().insert(
                calendarId=calendar_id,
                body=event_data,
                conferenceDataVersion=1 if params.get("add_conference", False) else 0,
                sendUpdates=params.get("send_updates", "none")
            ).execute()
            
            return self._create_success_result({
                "event": created_event,
                "created": True,
                "event_id": created_event["id"],
                "html_link": created_event.get("htmlLink")
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to create event: {str(e)}")
    
    async def _update_event(self, params: Dict[str, Any]) -> ToolResult:
        """Update calendar event"""
        error = validate_required_params(params, ["event_id"])
        if error:
            return self._create_error_result(error)
        
        event_id = params["event_id"]
        calendar_id = params.get("calendar_id", self.default_calendar_id)
        
        try:
            # First get the existing event
            event = self.calendar_service.events().get(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            
            # Update fields
            for field in ["summary", "description", "location"]:
                if field in params:
                    event[field] = params[field]
            
            # Handle start and end times
            if "start_time" in params and "end_time" in params:
                event["start"] = {"dateTime": params["start_time"]}
                event["end"] = {"dateTime": params["end_time"]}
            elif "start_date" in params and "end_date" in params:
                event["start"] = {"date": params["start_date"]}
                event["end"] = {"date": params["end_date"]}
            
            # Handle attendees
            if "attendees" in params:
                event["attendees"] = [
                    {"email": email} for email in params["attendees"]
                ]
            
            # Handle reminders
            if "reminders" in params:
                event["reminders"] = params["reminders"]
            
            # Handle recurrence
            if "recurrence" in params:
                event["recurrence"] = params["recurrence"]
            
            updated_event = self.calendar_service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
                sendUpdates=params.get("send_updates", "none")
            ).execute()
            
            return self._create_success_result({
                "event": updated_event,
                "updated": True,
                "event_id": updated_event["id"]
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to update event: {str(e)}")
    
    async def _delete_event(self, params: Dict[str, Any]) -> ToolResult:
        """Delete calendar event"""
        error = validate_required_params(params, ["event_id"])
        if error:
            return self._create_error_result(error)
        
        event_id = params["event_id"]
        calendar_id = params.get("calendar_id", self.default_calendar_id)
        
        try:
            self.calendar_service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates=params.get("send_updates", "none")
            ).execute()
            
            return self._create_success_result({
                "deleted": True,
                "event_id": event_id
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to delete event: {str(e)}")
    
    async def _check_availability(self, params: Dict[str, Any]) -> ToolResult:
        """Check availability for a time period"""
        error = validate_required_params(params, ["time_min", "time_max"])
        if error:
            return self._create_error_result(error)
        
        calendar_id = params.get("calendar_id", self.default_calendar_id)
        time_min = params["time_min"]
        time_max = params["time_max"]
        
        try:
            # Get events in the specified time range
            events_result = self.calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            events = events_result.get("items", [])
            
            # Check if there are any events in the time range
            is_available = len(events) == 0
            
            return self._create_success_result({
                "available": is_available,
                "events": events if not is_available else [],
                "count": len(events)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to check availability: {str(e)}")
    
    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition"""
        return types.Tool(
            name="google_calendar",
            description="Google Calendar operations for events and scheduling",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "list_calendars", "get_calendar",
                            "list_events", "get_event", "create_event",
                            "update_event", "delete_event", "check_availability"
                        ],
                        "description": "The action to perform"
                    },
                    "calendar_id": {"type": "string", "description": "Calendar ID (default: primary)"},
                    "event_id": {"type": "string", "description": "Event ID"},
                    "summary": {"type": "string", "description": "Event summary/title"},
                    "description": {"type": "string", "description": "Event description"},
                    "location": {"type": "string", "description": "Event location"},
                    "start_time": {"type": "string", "description": "Event start time (ISO format)"},
                    "end_time": {"type": "string", "description": "Event end time (ISO format)"},
                    "start_date": {"type": "string", "description": "Event start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "Event end date (YYYY-MM-DD)"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee emails"},
                    "reminders": {"type": "object", "description": "Event reminders configuration"},
                    "recurrence": {"type": "array", "items": {"type": "string"}, "description": "Recurrence rules (RRULE)"},
                    "add_conference": {"type": "boolean", "description": "Add Google Meet conference"},
                    "send_updates": {"type": "string", "enum": ["all", "externalOnly", "none"], "description": "Send updates to attendees"},
                    "time_min": {"type": "string", "description": "Minimum time for queries (ISO format)"},
                    "time_max": {"type": "string", "description": "Maximum time for queries (ISO format)"},
                    "max_results": {"type": "integer", "description": "Maximum results to return"},
                    "q": {"type": "string", "description": "Search query"},
                    "single_events": {"type": "boolean", "description": "Expand recurring events"},
                    "order_by": {"type": "string", "description": "Order results by"},
                    "page_token": {"type": "string", "description": "Page token for pagination"}
                },
                "required": ["action"]
            }
        )
    
    async def cleanup(self):
        """Clean up resources"""
        # No specific cleanup needed for Google Calendar
        self.logger.info("Google Calendar tool cleaned up")