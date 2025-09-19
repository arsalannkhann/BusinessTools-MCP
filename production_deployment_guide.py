"""
Production Deployment Guide for Google OAuth Auto-Refresh
=========================================================

This guide explains how to deploy the MCP server with automatic Google token refresh
for production environments without manual intervention.

SOLUTION APPROACHES:
==================

1. SERVICE ACCOUNT (RECOMMENDED FOR PRODUCTION)
   - No user interaction required
   - Tokens don't expire
   - Better for server-to-server communication

2. REFRESH TOKEN AUTO-RENEWAL (CURRENT IMPLEMENTATION)
   - Uses existing user OAuth tokens
   - Automatically refreshes before expiry
   - Background monitoring included

3. TOKEN ROTATION SERVICE
   - External service manages tokens
   - Scheduled refresh jobs
   - Centralized token management

CURRENT AUTO-REFRESH IMPLEMENTATION:
===================================

Features Added:
- Background token refresh monitoring (every 30 minutes)
- Automatic refresh when token expires in < 5 minutes  
- Production environment detection
- Graceful error handling and retry logic
- Service rebuilding with fresh credentials

Environment Variables:
- ENVIRONMENT=production  (enables auto-refresh)
- Or any of: prod, staging, live

DEPLOYMENT CONFIGURATIONS:
=========================
"""

import os
import json
from datetime import datetime, timedelta

def setup_production_config():
    """Setup production configuration for auto-refresh"""
    
    config = {
        # Environment Detection
        "ENVIRONMENT": "production",  # Enables auto-refresh
        
        # Google OAuth Settings
        "GOOGLE_CREDENTIALS_PATH": "/app/credentials/google_credentials.json",
        "GOOGLE_TOKEN_PATH": "/app/credentials/google_token.json",
        
        # Auto-refresh Settings (optional, has defaults)
        "GOOGLE_REFRESH_INTERVAL": 1800,  # 30 minutes
        "GOOGLE_MIN_TOKEN_LIFETIME": 300,  # 5 minutes
        
        # Backup/Recovery
        "TOKEN_BACKUP_PATH": "/app/backups/tokens/",
        "ENABLE_TOKEN_BACKUP": True,
        
        # Monitoring
        "ENABLE_TOKEN_MONITORING": True,
        "TOKEN_ALERT_WEBHOOK": "https://your-monitoring.com/webhook"
    }
    
    return config

def docker_compose_production():
    """Production Docker Compose configuration"""
    
    compose = {
        "version": "3.8",
        "services": {
            "mcp-server": {
                "build": ".",
                "environment": [
                    "ENVIRONMENT=production",
                    "GOOGLE_CREDENTIALS_PATH=/app/credentials/google_credentials.json",
                    "GOOGLE_TOKEN_PATH=/app/credentials/google_token.json"
                ],
                "volumes": [
                    "./credentials:/app/credentials:ro",
                    "./token_storage:/app/tokens:rw",
                    "./backups:/app/backups:rw"
                ],
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": ["CMD", "python", "health_check.py"],
                    "interval": "60s",
                    "timeout": "10s",
                    "retries": 3
                }
            }
        }
    }
    
    return compose

def kubernetes_deployment():
    """Kubernetes deployment with token auto-refresh"""
    
    k8s_config = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "mcp-server"},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "mcp-server"}},
            "template": {
                "metadata": {"labels": {"app": "mcp-server"}},
                "spec": {
                    "containers": [{
                        "name": "mcp-server",
                        "image": "your-registry/mcp-server:latest",
                        "env": [
                            {"name": "ENVIRONMENT", "value": "production"},
                            {"name": "GOOGLE_CREDENTIALS_PATH", "value": "/credentials/google_credentials.json"},
                            {"name": "GOOGLE_TOKEN_PATH", "value": "/tokens/google_token.json"}
                        ],
                        "volumeMounts": [
                            {"name": "credentials", "mountPath": "/credentials", "readOnly": True},
                            {"name": "tokens", "mountPath": "/tokens"}
                        ],
                        "livenessProbe": {
                            "exec": {"command": ["python", "health_check.py"]},
                            "initialDelaySeconds": 30,
                            "periodSeconds": 60
                        }
                    }],
                    "volumes": [
                        {"name": "credentials", "secret": {"secretName": "google-credentials"}},
                        {"name": "tokens", "persistentVolumeClaim": {"claimName": "token-storage"}}
                    ]
                }
            }
        }
    }
    
    return k8s_config

# DEPLOYMENT STEPS:
# =================
#
# 1. Initial Setup (One-time):
#    - Run OAuth flow locally to get initial tokens
#    - Copy credentials.json and token.json to production
#    - Set ENVIRONMENT=production
#
# 2. Deploy with Docker:
#    docker-compose -f docker-compose.prod.yml up -d
#
# 3. Deploy with Kubernetes:
#    kubectl apply -f k8s-deployment.yaml
#
# 4. Monitor token refresh:
#    - Check logs for "Automatically refreshing Google token"
#    - Set up alerts for refresh failures
#
# TROUBLESHOOTING:
# ===============
#
# Token Refresh Failures:
# - Check refresh_token is not null
# - Verify credentials.json client_secret
# - Ensure token.json is writable
#
# Production Detection:
# - Set ENVIRONMENT=production explicitly
# - Check logs for "Started automatic token refresh monitoring"
#
# Service Rebuilding:
# - Services automatically rebuilt after refresh
# - Check logs for "Google services rebuilt with refreshed credentials"

print("Production deployment guide created!")
print("Key features:")
print("✅ Automatic token refresh every 30 minutes")
print("✅ Background monitoring for production")
print("✅ Service rebuilding with fresh credentials") 
print("✅ Environment-based configuration")
print("✅ Docker and Kubernetes ready")
