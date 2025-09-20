"""Base classes and interfaces for sales tools"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from mcp import types

logger = logging.getLogger(__name__)

def validate_required_params(params: dict[str, Any], required_params: list[str]) -> str | None:
    """Validate that required parameters are present"""
    missing = [param for param in required_params if param not in params]
    if missing:
        return f"Missing required parameters: {', '.join(missing)}"
    return None

@dataclass
class ToolResult:
    """Standardized tool execution result"""
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result: dict[str, Any] = {
            "success": self.success
        }

        if self.data is not None:
            result["data"] = self.data

        if self.error:
            result["error"] = self.error

        if self.metadata:
            result["metadata"] = self.metadata

        return result

class SalesTool(ABC):
    """Abstract base class for all sales tools"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"tools.{name}")

    @abstractmethod
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize the tool with configuration"""

    @abstractmethod
    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute a tool action"""

    @abstractmethod
    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition for registration"""

    async def cleanup(self):
        """Clean up resources (optional override)"""

    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return True

    def _create_success_result(self, data: Any = None, metadata: dict[str, Any] | None = None) -> ToolResult:
        """Helper to create success result"""
        return ToolResult(success=True, data=data, metadata=metadata)

    def _create_error_result(self, error: str, metadata: dict[str, Any] | None = None) -> ToolResult:
        """Helper to create error result"""
        return ToolResult(success=False, error=error, metadata=metadata)

class SalesToolRegistry:
    """Registry and manager for all sales tools"""

    def __init__(self):
        self.tools: dict[str, SalesTool] = {}
        self.logger = logging.getLogger("tools.registry")

    async def initialize_tools(self, settings, google_auth=None):
        """Initialize all available tools, always registering them even if initialization fails"""
        from .apollo_tool import ApolloTool
        from .calendly_tool import CalendlyTool
        from .gmail_tool import GmailTool
        from .google_calendar_tool import GoogleCalendarTool
        from .google_drive_tool import GoogleDriveTool
        from .google_meet_tool import GoogleMeetTool
        from .google_search_tool import GoogleSearchTool
        from .google_sheets_tool import GoogleSheetsTool
        from .hubspot_tool import HubSpotTool
        from .linkedin_sales_navigator_tool import LinkedInSalesNavigatorTool
        from .outreach_tool import OutreachTool
        from .stripe_tool import StripeTool
        from .twilio_tool import TwilioTool

        tool_classes = [
            CalendlyTool,
            GoogleCalendarTool,
            GoogleMeetTool,
            GmailTool,
            GoogleDriveTool,
            GoogleSheetsTool,
            GoogleSearchTool,
            TwilioTool,
            HubSpotTool,
            StripeTool,
            LinkedInSalesNavigatorTool,
            ApolloTool,
            OutreachTool
        ]

        initialized_count = 0
        working_count = 0
        for tool_class in tool_classes:
            try:
                tool = tool_class()
                init_ok = False
                try:
                    init_ok = await tool.initialize(settings, google_auth)
                except Exception as init_err:
                    self.logger.warning(f"Tool {tool_class.__name__} failed to initialize: {init_err}")

                if init_ok and tool.is_configured():
                    self.logger.info(f"✅ Initialized tool: {tool.name}")
                    tool._configured = True
                    working_count += 1
                else:
                    self.logger.warning(f"⚠️  Tool {getattr(tool, 'name', tool_class.__name__)} not fully configured, registering with limited functionality")
                    tool._configured = False

                # Always register the tool
                self.tools[tool.name] = tool
                initialized_count += 1
            except Exception as e:
                self.logger.error(f"❌ Error creating tool {tool_class.__name__}: {e}")

        self.logger.info(f"Tool Registry Summary: {working_count} working tools, {initialized_count-working_count} limited tools, {initialized_count} total registered out of {len(tool_classes)} available")

    def list_mcp_tools(self) -> list[types.Tool]:
        """List all available tools in MCP format"""
        tools = []
        for tool in self.tools.values():
            try:
                mcp_tool = tool.get_mcp_tool_definition()
                # Ensure name and schema are properly set
                if not getattr(mcp_tool, "name", None) or getattr(mcp_tool, "name", None) is False:
                    self.logger.error(f"Invalid tool name for {tool}")
                    continue
                if not hasattr(mcp_tool, "inputSchema"):
                    self.logger.error(f"Missing inputSchema for tool {getattr(mcp_tool, 'name', None)}")
                    continue
                tools.append(mcp_tool)
            except Exception as e:
                self.logger.error(f"Error getting MCP definition for {tool}: {e}")
        return tools

    def get_tool(self, name: str) -> SalesTool | None:
        """Get a tool by name"""
        return self.tools.get(name)

    async def execute_tool(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name"""
        if name not in self.tools:
            return {
                "success": False,
                "error": f"Tool not found: {name}"
            }

        tool = self.tools[name]

        try:
            # Extract action from params
            if "action" not in params:
                return {
                    "success": False,
                    "error": "Missing required parameter: action"
                }

            action = params.pop("action")

            # Execute the tool action
            result = await tool.execute(action, params)

            # Convert to dict for JSON serialization
            return result.to_dict()

        except Exception as e:
            self.logger.error(f"Error executing tool {name}: {e}")
            return {
                "success": False,
                "error": f"Tool execution error: {e!s}"
            }

    async def cleanup(self):
        """Clean up all tools"""
        for name, tool in self.tools.items():
            try:
                await tool.cleanup()
                self.logger.debug(f"Cleaned up tool: {name}")
            except Exception as e:
                self.logger.error(f"Error cleaning up tool {name}: {e}")

        self.tools.clear()
        self.logger.info("All tools cleaned up")
