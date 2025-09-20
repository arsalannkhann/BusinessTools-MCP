#!/usr/bin/env python3
"""
Comprehensive tool testing script
Tests all configured tools to identify any issues
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime

# Import the sales MCP server
from sales_mcp_server import SalesMCPServer
from config.settings import Settings


class ToolTester:
    def __init__(self):
        self.server = SalesMCPServer()
        self.settings = Settings()
        self.test_results = {}

    async def initialize(self):
        """Initialize the MCP server"""
        print("🔄 Initializing MCP Server...")
        try:
            await self.server.initialize()
            print("✅ MCP Server initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize MCP Server: {e}")
            return False

    async def test_tool(self, tool_name: str, test_cases: list):
        """Test a specific tool with given test cases"""
        print(f"\n🧪 Testing {tool_name}...")
        
        if tool_name not in self.server.tool_registry.tools:
            print(f"❌ Tool {tool_name} not found in registry")
            return {"status": "not_found", "tests": []}

        tool = self.server.tool_registry.tools[tool_name]
        test_results = []

        for test_case in test_cases:
            test_name = test_case["name"]
            action = test_case["action"]
            params = test_case.get("params", {})
            should_succeed = test_case.get("should_succeed", True)

            print(f"  🔸 {test_name}")
            
            try:
                result = await tool.execute(action, params)
                
                if hasattr(result, 'success'):
                    success = result.success
                    data = result.data if hasattr(result, 'data') else str(result)
                    error = result.error if hasattr(result, 'error') else None
                else:
                    success = True
                    data = str(result)
                    error = None

                if should_succeed:
                    if success:
                        print(f"    ✅ Success: {str(data)[:100]}...")
                        test_results.append({
                            "name": test_name,
                            "status": "passed",
                            "data": data,
                            "error": error
                        })
                    else:
                        print(f"    ❌ Expected success but got error: {error}")
                        test_results.append({
                            "name": test_name,
                            "status": "failed",
                            "data": data,
                            "error": error
                        })
                else:
                    if success:
                        print(f"    ⚠️  Expected failure but got success: {str(data)[:100]}...")
                        test_results.append({
                            "name": test_name,
                            "status": "unexpected_success",
                            "data": data,
                            "error": error
                        })
                    else:
                        print(f"    ✅ Expected failure: {error}")
                        test_results.append({
                            "name": test_name,
                            "status": "passed",
                            "data": data,
                            "error": error
                        })

            except Exception as e:
                print(f"    💥 Exception: {str(e)}")
                test_results.append({
                    "name": test_name,
                    "status": "exception",
                    "data": None,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })

        return {"status": "tested", "tests": test_results}

    async def run_all_tests(self):
        """Run comprehensive tests on all tools"""
        print("🚀 Starting comprehensive tool testing...")
        print("=" * 60)

        # Test configurations for each tool
        test_configs = {
            "gmail": [
                {
                    "name": "Get Gmail profile",
                    "action": "get_profile",
                    "params": {},
                    "should_succeed": True
                },
                {
                    "name": "List recent messages",
                    "action": "list_messages", 
                    "params": {"max_results": 5},
                    "should_succeed": True
                },
                {
                    "name": "Send test email (will fail without recipient)",
                    "action": "send_email",
                    "params": {"to": "", "subject": "Test", "body": "Test"},
                    "should_succeed": False
                }
            ],
            "google_calendar": [
                {
                    "name": "List calendars",
                    "action": "list_calendars",
                    "params": {},
                    "should_succeed": True
                },
                {
                    "name": "Get upcoming events",
                    "action": "list_events",
                    "params": {"max_results": 5},
                    "should_succeed": True
                }
            ],
            "google_drive": [
                {
                    "name": "List files",
                    "action": "list_files",
                    "params": {"max_results": 10},
                    "should_succeed": True
                },
                {
                    "name": "Get drive info",
                    "action": "get_about",
                    "params": {},
                    "should_succeed": True
                }
            ],
            "google_sheets": [
                {
                    "name": "Get sheet info (will fail without sheet_id)",
                    "action": "get_sheet_info",
                    "params": {"sheet_id": ""},
                    "should_succeed": False
                }
            ],
            "google_search": [
                {
                    "name": "Search for 'Python programming'",
                    "action": "search",
                    "params": {"query": "Python programming", "num_results": 5},
                    "should_succeed": True
                }
            ],
            "google_meet": [
                {
                    "name": "Create meeting",
                    "action": "create_meeting", 
                    "params": {"title": "Test Meeting", "start_time": "2025-09-21T10:00:00Z"},
                    "should_succeed": True
                }
            ],
            "twilio": [
                {
                    "name": "Get account info",
                    "action": "get_account_info",
                    "params": {},
                    "should_succeed": True
                },
                {
                    "name": "Send SMS (will fail without valid number)",
                    "action": "send_sms",
                    "params": {"to": "", "message": "Test"},
                    "should_succeed": False
                }
            ],
            "hubspot": [
                {
                    "name": "Get account info",
                    "action": "get_account_info", 
                    "params": {},
                    "should_succeed": True
                },
                {
                    "name": "List contacts",
                    "action": "list_contacts",
                    "params": {"limit": 5},
                    "should_succeed": True
                }
            ]
        }

        # Run tests for each configured tool
        for tool_name, test_cases in test_configs.items():
            self.test_results[tool_name] = await self.test_tool(tool_name, test_cases)

        # Generate summary report
        self.generate_report()

    def generate_report(self):
        """Generate a comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY REPORT")
        print("=" * 60)

        total_tools = len(self.test_results)
        working_tools = []
        problem_tools = []

        for tool_name, result in self.test_results.items():
            if result["status"] == "not_found":
                problem_tools.append(f"{tool_name}: NOT FOUND")
                continue

            tests = result["tests"]
            passed = len([t for t in tests if t["status"] == "passed"])
            failed = len([t for t in tests if t["status"] in ["failed", "exception"]])
            total = len(tests)

            if failed == 0:
                working_tools.append(f"✅ {tool_name}: {passed}/{total} tests passed")
            else:
                problem_tools.append(f"❌ {tool_name}: {passed}/{total} tests passed, {failed} issues")

        print(f"\n🏆 WORKING TOOLS ({len(working_tools)}):")
        for tool in working_tools:
            print(f"  {tool}")

        if problem_tools:
            print(f"\n⚠️  TOOLS WITH ISSUES ({len(problem_tools)}):")
            for tool in problem_tools:
                print(f"  {tool}")

        # Detailed error analysis
        print(f"\n🔍 DETAILED ISSUE ANALYSIS:")
        for tool_name, result in self.test_results.items():
            if result["status"] == "tested":
                failed_tests = [t for t in result["tests"] if t["status"] in ["failed", "exception"]]
                if failed_tests:
                    print(f"\n  {tool_name} Issues:")
                    for test in failed_tests:
                        print(f"    • {test['name']}: {test['error']}")

        print(f"\n📈 OVERALL RESULTS:")
        print(f"  • Total tools tested: {total_tools}")
        print(f"  • Fully working tools: {len(working_tools)}")
        print(f"  • Tools with issues: {len(problem_tools)}")
        print(f"  • Success rate: {len(working_tools)}/{total_tools} ({len(working_tools)/total_tools*100:.1f}%)")


async def main():
    """Main test runner"""
    tester = ToolTester()
    
    if not await tester.initialize():
        sys.exit(1)
    
    await tester.run_all_tests()
    print("\n🎯 Tool testing completed!")


if __name__ == "__main__":
    asyncio.run(main())
