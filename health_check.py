#!/usr/bin/env python3
"""
Health Check Script for MCP Server
Monitors Google token status and service health for production deployments
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

async def check_google_token_health() -> Dict[str, Any]:
    """Check Google token health status"""
    try:
        token_file = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
        
        if not os.path.exists(token_file):
            return {
                'status': 'error',
                'message': f'Token file not found: {token_file}',
                'healthy': False
            }
        
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        # Check token expiry
        expiry_str = token_data.get('expiry')
        if not expiry_str:
            return {
                'status': 'warning', 
                'message': 'No expiry information in token',
                'healthy': True  # Still functional
            }
        
        # Parse expiry time
        try:
            expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            time_until_expiry = expiry_time - datetime.now(expiry_time.tzinfo)
            minutes_until_expiry = time_until_expiry.total_seconds() / 60
            
            if minutes_until_expiry < 0:
                return {
                    'status': 'error',
                    'message': f'Token expired {abs(minutes_until_expiry):.0f} minutes ago',
                    'healthy': False,
                    'expiry': expiry_str,
                    'expired': True
                }
            elif minutes_until_expiry < 60:  # Less than 1 hour
                return {
                    'status': 'warning',
                    'message': f'Token expires in {minutes_until_expiry:.0f} minutes',
                    'healthy': True,
                    'expiry': expiry_str,
                    'minutes_until_expiry': minutes_until_expiry
                }
            else:
                return {
                    'status': 'healthy',
                    'message': f'Token valid for {minutes_until_expiry/60:.1f} hours',
                    'healthy': True,
                    'expiry': expiry_str,
                    'hours_until_expiry': minutes_until_expiry / 60
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Could not parse expiry time: {e}',
                'healthy': False
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error checking token health: {e}',
            'healthy': False
        }

async def check_server_health() -> Dict[str, Any]:
    """Check overall server health"""
    try:
        from tools.base import SalesToolRegistry
        from config.settings import Settings
        
        # Test tool registry initialization
        registry = SalesToolRegistry()
        settings = Settings()
        await registry.initialize_tools(settings)
        
        configured_count = len([t for t in registry.tools.values() if t.is_configured()])
        total_count = len(registry.tools)
        
        await registry.cleanup()
        
        return {
            'status': 'healthy',
            'message': f'{configured_count}/{total_count} tools configured',
            'healthy': True,
            'tools': {
                'configured': configured_count,
                'total': total_count,
                'percentage': (configured_count / total_count * 100) if total_count > 0 else 0
            }
        }
        
    except Exception as e:
        return {
            'status': 'error', 
            'message': f'Server health check failed: {e}',
            'healthy': False
        }

async def check_environment_config() -> Dict[str, Any]:
    """Check environment configuration"""
    try:
        environment = os.getenv('ENVIRONMENT', 'development').lower()
        is_production = environment in ['production', 'prod', 'staging', 'live']
        
        required_vars = [
            'GOOGLE_CREDENTIALS_PATH',
            'GOOGLE_TOKEN_PATH'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        return {
            'status': 'healthy' if not missing_vars else 'warning',
            'message': f'Environment: {environment}, Missing vars: {missing_vars}' if missing_vars else f'Environment: {environment}',
            'healthy': True,
            'environment': environment,
            'is_production': is_production,
            'missing_vars': missing_vars
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Environment check failed: {e}',
            'healthy': False
        }

async def main():
    """Main health check function"""
    print("🏥 MCP Server Health Check")
    print("=" * 50)
    
    # Check all health aspects
    checks = [
        ("Google Token", check_google_token_health),
        ("Server Health", check_server_health), 
        ("Environment", check_environment_config)
    ]
    
    overall_healthy = True
    results = {}
    
    for name, check_func in checks:
        print(f"\n🔍 Checking {name}...")
        try:
            result = await check_func()
            results[name.lower().replace(' ', '_')] = result
            
            status_icon = {
                'healthy': '✅',
                'warning': '⚠️',
                'error': '❌'
            }.get(result['status'], '❓')
            
            print(f"{status_icon} {name}: {result['message']}")
            
            if not result['healthy']:
                overall_healthy = False
                
        except Exception as e:
            print(f"❌ {name}: Check failed - {e}")
            overall_healthy = False
            results[name.lower().replace(' ', '_')] = {
                'status': 'error',
                'message': f'Check failed: {e}',
                'healthy': False
            }
    
    # Summary
    print(f"\n📊 Overall Health: {'✅ HEALTHY' if overall_healthy else '❌ UNHEALTHY'}")
    
    # Exit with appropriate code for monitoring systems
    exit_code = 0 if overall_healthy else 1
    
    # Output JSON for programmatic parsing
    if '--json' in sys.argv:
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'overall_healthy': overall_healthy,
            'checks': results
        }
        print(json.dumps(health_data, indent=2))
    
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
