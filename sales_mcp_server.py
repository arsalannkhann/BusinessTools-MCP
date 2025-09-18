
"""
Sales MCP Server - Main Entry Point
A production-ready MCP server providing 15 essential sales tools.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import signal
import sys
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server

# Local imports
from config.settings import Settings
from config.google_auth import GoogleAuthManager
from tools.base import SalesToolRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SalesMCPServer:
    """Main Sales MCP Server class"""
    
    def __init__(self):
        self.app = Server("sales-mcp-server")
        self.settings = Settings()
        self.google_auth = None
        self.tool_registry = SalesToolRegistry()
        self.running = False
        
    async def initialize(self):
        """Initialize server components"""
        try:
            # Initialize Google Auth if configured
            if self.settings.google_credentials_path:
                self.google_auth = GoogleAuthManager(self.settings)
                await self.google_auth.initialize()
                logger.info("Google Auth initialized successfully")
            
            # Initialize and register all tools
            await self.tool_registry.initialize_tools(self.settings, self.google_auth)
            logger.info(f"Initialized {len(self.tool_registry.tools)} sales tools")
            
            # Register MCP handlers
            self._register_handlers()
            
        except Exception as e:
            logger.error(f"Server initialization failed: {e}")
            raise
    
    def _register_handlers(self):
        """Register MCP server handlers"""
        
        @self.app.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List all available sales tools"""
            return self.tool_registry.list_mcp_tools()
        
        @self.app.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Optional[Dict[str, Any]] = None
        ) -> List[types.TextContent]:
            """Route tool calls to appropriate handlers"""
            if arguments is None:
                arguments = {}
                
            try:
                result = await self.tool_registry.execute_tool(name, arguments)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                logger.error(f"Tool execution failed for {name}: {str(e)}")
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "error": f"Tool execution failed: {str(e)}",
                        "tool": name
                    })
                )]
    
    async def run(self):
        """Run the MCP server"""
        self.running = True
        
        try:
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                logger.info("Sales MCP Server started successfully")
                await self.app.run(
                    read_stream,
                    write_stream,
                    self.app.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"Server runtime error: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up server resources"""
        self.running = False
        
        try:
            if self.google_auth:
                await self.google_auth.cleanup()
            
            await self.tool_registry.cleanup()
            logger.info("Server cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        if self.running:
            asyncio.create_task(self.cleanup())
        sys.exit(0)

async def main():
    """Main async function"""
    server = SalesMCPServer()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, server.handle_signal)
    signal.signal(signal.SIGTERM, server.handle_signal)
    
    try:
        await server.initialize()
        await server.run()
    except KeyboardInterrupt:
        logger.info("Shutdown requested (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting Sales MCP Server...")
    asyncio.run(main())