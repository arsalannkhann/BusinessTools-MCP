"""
Tests for the main MCP server functionality
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest

from sales_mcp_server import SalesMCPServer


class TestSalesMCPServer:
    """Test Sales MCP Server functionality"""

    @pytest.fixture
    def mock_server(self):
        """Create a mocked server instance"""
        with patch("config.settings.Settings"), \
             patch("tools.base.SalesToolRegistry") as mock_registry:
            server = SalesMCPServer()
            server.tool_registry = mock_registry
            return server

    @pytest.mark.asyncio
    async def test_server_initialization(self, mock_server):
        """Test server initialization"""
        mock_server.tool_registry.initialize_tools = AsyncMock()
        mock_server.google_auth = None

        await mock_server.initialize()

        # Verify that tool registry was initialized
        mock_server.tool_registry.initialize_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_server):
        """Test server cleanup"""
        mock_server.tool_registry.cleanup = AsyncMock()
        mock_server.google_auth = None

        await mock_server.cleanup()

        # Verify cleanup was called
        mock_server.tool_registry.cleanup.assert_called_once()
        assert mock_server.running is False
