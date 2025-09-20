#!/usr/bin/env python3
"""
Standalone Tool Testing Script for Sales MCP Server
Tests all configured tools without starting the web server
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from sales_mcp_server import SalesMCPServer

class ToolTester:
    def __init__(self):
        """Initialize the tool tester"""
        self.server = None
        self.results = {}
        
    async def initialize_server(self):
        """Initialize the MCP server"""
        try:
            logger.info("Initializing MCP Server...")
            self.server = SalesMCPServer()
            await self.server.initialize()
            logger.info("MCP Server initialized successfully")
            
            # Get tool registry
            if hasattr(self.server, 'tool_registry') and self.server.tool_registry:
                working_tools = len([tool for tool in self.server.tool_registry.tools.values() if getattr(tool, '_configured', False)])
                limited_tools = len([tool for tool in self.server.tool_registry.tools.values() if not getattr(tool, '_configured', False)])
                logger.info(f"Found {working_tools} working tools and {limited_tools} limited tools")
                return True
            else:
                logger.error("No tool registry found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            return False
    
    async def test_tool(self, tool_name: str) -> Dict[str, Any]:
        """Test a specific tool with appropriate test actions"""
        logger.info(f"Testing tool: {tool_name}")
        
        tool_config = {
            'gmail': [
                {'action': 'get_profile', 'args': {}},
                {'action': 'list_messages', 'args': {'max_results': 5}},
            ],
            'google_calendar': [
                {'action': 'list_calendars', 'args': {}},
                {'action': 'get_upcoming_events', 'args': {'max_results': 5}},
            ],
            'google_drive': [
                {'action': 'list_files', 'args': {'max_results': 5}},
            ],
            'google_sheets': [
                {'action': 'list_spreadsheets', 'args': {}},
            ],
            'google_meet': [
                {'action': 'list_upcoming_meetings', 'args': {}},
            ],
            'google_search': [
                {'action': 'search', 'args': {'query': 'test search', 'num_results': 3}},
            ],
            'twilio': [
                {'action': 'get_account_info', 'args': {}},
            ],
            'hubspot': [
                {'action': 'get_account_info', 'args': {}},
                {'action': 'search_contacts', 'args': {'query': 'test', 'limit': 5}},
            ]
        }
        
        test_results = {
            'tool_name': tool_name,
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {'passed': 0, 'failed': 0, 'errors': []}
        }
        
        # Get tool from registry
        try:
            if not self.server.tool_registry or tool_name not in self.server.tool_registry.tools:
                test_results['summary']['errors'].append(f"Tool {tool_name} not found in registry")
                return test_results
            
            tool = self.server.tool_registry.tools[tool_name]
            
            # Check if tool is configured
            if not getattr(tool, '_configured', False):
                test_results['summary']['errors'].append(f"Tool {tool_name} is not fully configured")
                logger.warning(f"Tool {tool_name} is not fully configured, skipping tests")
                return test_results
            
            # Run configured tests for this tool
            if tool_name in tool_config:
                for test_case in tool_config[tool_name]:
                    test_result = {
                        'action': test_case['action'],
                        'args': test_case['args'],
                        'success': False,
                        'response': None,
                        'error': None
                    }
                    
                    try:
                        logger.info(f"  Testing {tool_name}.{test_case['action']}...")
                        
                        # Execute the tool action
                        result = await tool.execute(test_case['action'], test_case['args'])
                        
                        test_result['success'] = True
                        test_result['response'] = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                        test_results['summary']['passed'] += 1
                        logger.info(f"  ✅ {tool_name}.{test_case['action']} - SUCCESS")
                        
                    except Exception as e:
                        test_result['error'] = str(e)
                        test_results['summary']['failed'] += 1
                        test_results['summary']['errors'].append(f"{tool_name}.{test_case['action']}: {str(e)}")
                        logger.error(f"  ❌ {tool_name}.{test_case['action']} - ERROR: {e}")
                    
                    test_results['tests'].append(test_result)
            else:
                test_results['summary']['errors'].append(f"No test configuration found for {tool_name}")
                
        except Exception as e:
            test_results['summary']['errors'].append(f"Failed to get tool {tool_name}: {str(e)}")
            logger.error(f"Failed to get tool {tool_name}: {e}")
        
        return test_results
    
    async def run_all_tests(self):
        """Run tests for all configured tools"""
        if not await self.initialize_server():
            return
        
        logger.info("Starting comprehensive tool testing...")
        
        # Get list of working tools
        working_tools = []
        if self.server.tool_registry:
            for tool_name, tool in self.server.tool_registry.tools.items():
                if getattr(tool, '_configured', False):
                    working_tools.append(tool_name)
        
        logger.info(f"Testing {len(working_tools)} working tools: {', '.join(working_tools)}")
        
        # Test each tool
        all_results = {}
        for tool_name in working_tools:
            result = await self.test_tool(tool_name)
            all_results[tool_name] = result
        
        # Generate summary report
        self.generate_report(all_results)
        
        return all_results
    
    def generate_report(self, results: Dict[str, Any]):
        """Generate a comprehensive test report"""
        logger.info("\n" + "="*80)
        logger.info("COMPREHENSIVE TOOL TEST REPORT")
        logger.info("="*80)
        
        total_tools = len(results)
        total_tests = sum(len(result['tests']) for result in results.values())
        total_passed = sum(result['summary']['passed'] for result in results.values())
        total_failed = sum(result['summary']['failed'] for result in results.values())
        
        logger.info(f"Tools Tested: {total_tools}")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {total_passed}")
        logger.info(f"Failed: {total_failed}")
        logger.info(f"Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
        
        logger.info("\nDETAILED RESULTS:")
        logger.info("-" * 40)
        
        for tool_name, result in results.items():
            passed = result['summary']['passed']
            failed = result['summary']['failed']
            total = passed + failed
            
            status = "✅ PASS" if failed == 0 and total > 0 else "❌ FAIL" if failed > 0 else "⚠️  NO TESTS"
            logger.info(f"{tool_name:20} | {status:8} | {passed}/{total} passed")
            
            # Show errors if any
            if result['summary']['errors']:
                for error in result['summary']['errors']:
                    logger.info(f"    ERROR: {error}")
        
        # Gmail specific analysis
        if 'gmail' in results:
            logger.info("\nGMAIL ANALYSIS:")
            logger.info("-" * 40)
            gmail_result = results['gmail']
            if gmail_result['summary']['errors']:
                logger.info("❌ Gmail has issues:")
                for error in gmail_result['summary']['errors']:
                    logger.info(f"  - {error}")
            else:
                logger.info("✅ Gmail appears to be working correctly")
                for test in gmail_result['tests']:
                    if test['success']:
                        logger.info(f"  ✅ {test['action']}: SUCCESS")
                    else:
                        logger.info(f"  ❌ {test['action']}: {test['error']}")
        
        logger.info("\n" + "="*80)

async def main():
    """Main testing function"""
    tester = ToolTester()
    results = await tester.run_all_tests()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_results_{timestamp}.json"
    
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Test results saved to: {output_file}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")

if __name__ == "__main__":
    asyncio.run(main())
