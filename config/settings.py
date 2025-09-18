"""Configuration management for Sales MCP Server
Centralized settings and API key management
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class Settings:
    """Centralized configuration management"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Load settings from JSON if available
        self.settings_file = os.getenv("SETTINGS_FILE", "settings.json")
        self._load_settings()
        
        # Initialize all configuration sections
        self._init_google_config()
        self._init_crm_config()
        self._init_scheduling_config()
        self._init_outreach_config()
        self._init_communication_config()
        self._init_payment_config()
        self._init_server_config()
    
    def _load_settings(self):
        """Load settings from JSON file if it exists"""
        self.json_settings = {}
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    self.json_settings = json.load(f)
                logger.info(f"Loaded settings from {self.settings_file}")
            except Exception as e:
                logger.warning(f"Could not load settings file: {e}")
    
    def get(self, key: str, default: Any = None, section: Optional[str] = None) -> Any:
        """Get configuration value with fallback priority: env -> json -> default"""
        # Try environment variable first
        env_key = key.upper()
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        # Try JSON settings
        if section and section in self.json_settings:
            if key in self.json_settings[section]:
                return self.json_settings[section][key]
        elif key in self.json_settings:
            return self.json_settings[key]
        
        return default
    
    def _init_google_config(self):
        """Initialize Google services configuration"""
        self.google_credentials_path = self.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        self.google_token_path = self.get("GOOGLE_TOKEN_PATH", "token.json")
        self.google_scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.compose"
        ]
        
        # Gmail SMTP fallback
        self.gmail_email = self.get("GMAIL_EMAIL")
        self.gmail_app_password = self.get("GMAIL_APP_PASSWORD")
        
        # Google Search API
        self.google_search_api_key = self.get("GOOGLE_SEARCH_API_KEY")
        self.google_search_cse_id = self.get("GOOGLE_SEARCH_CSE_ID")
    
    def _init_crm_config(self):
        """Initialize CRM configurations"""
        # HubSpot
        self.hubspot_access_token = self.get("HUBSPOT_ACCESS_TOKEN")
        self.hubspot_api_key = self.get("HUBSPOT_API_KEY")
        
        # Salesforce
        self.salesforce_username = self.get("SALESFORCE_USERNAME")
        self.salesforce_password = self.get("SALESFORCE_PASSWORD")
        self.salesforce_security_token = self.get("SALESFORCE_SECURITY_TOKEN")
        self.salesforce_domain = self.get("SALESFORCE_DOMAIN", "login")
        
        # Pipedrive
        self.pipedrive_api_token = self.get("PIPEDRIVE_API_TOKEN")
        self.pipedrive_domain = self.get("PIPEDRIVE_DOMAIN")
    
    def _init_scheduling_config(self):
        """Initialize scheduling tool configurations"""
        # Calendly
        self.calendly_client_id = self.get("CALENDLY_CLIENT_ID")
        self.calendly_client_secret = self.get("CALENDLY_CLIENT_SECRET")
        self.calendly_access_token = self.get("CALENDLY_ACCESS_TOKEN")
        self.calendly_refresh_token = self.get("CALENDLY_REFRESH_TOKEN")
        
        # Zoom
        self.zoom_client_id = self.get("ZOOM_CLIENT_ID")
        self.zoom_client_secret = self.get("ZOOM_CLIENT_SECRET")
        self.zoom_account_id = self.get("ZOOM_ACCOUNT_ID")
        self.zoom_access_token = self.get("ZOOM_ACCESS_TOKEN")
    
    def _init_outreach_config(self):
        """Initialize outreach and prospecting tool configurations"""
        # Outreach.io
        self.outreach_client_id = self.get("OUTREACH_CLIENT_ID")
        self.outreach_client_secret = self.get("OUTREACH_CLIENT_SECRET")
        self.outreach_access_token = self.get("OUTREACH_ACCESS_TOKEN")
        
        # SalesLoft
        self.salesloft_api_key = self.get("SALESLOFT_API_KEY")
        
        # Apollo.io
        self.apollo_api_key = self.get("APOLLO_API_KEY")
        
        # LinkedIn
        self.linkedin_access_token = self.get("LINKEDIN_ACCESS_TOKEN")
        self.linkedin_client_id = self.get("LINKEDIN_CLIENT_ID")
        self.linkedin_client_secret = self.get("LINKEDIN_CLIENT_SECRET")
    
    def _init_communication_config(self):
        """Initialize communication tool configurations"""
        # Slack
        self.slack_bot_token = self.get("SLACK_BOT_TOKEN")
        self.slack_webhook_url = self.get("SLACK_WEBHOOK_URL")
        
        # Twilio (inherited from base)
        self.twilio_account_sid = self.get("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = self.get("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = self.get("TWILIO_PHONE_NUMBER")
    
    def _init_payment_config(self):
        """Initialize payment processing configurations"""
        # Stripe
        self.stripe_api_key = self.get("STRIPE_API_KEY")
        self.stripe_publishable_key = self.get("STRIPE_PUBLISHABLE_KEY")
        self.stripe_webhook_secret = self.get("STRIPE_WEBHOOK_SECRET")
    
    def _init_server_config(self):
        """Initialize server configuration"""
        self.server_name = self.get("MCP_SERVER_NAME", "sales-mcp-server")
        self.server_port = int(self.get("MCP_SERVER_PORT", "5000"))
        self.log_level = self.get("LOG_LEVEL", "INFO")
        self.debug = self.get("DEBUG", "false").lower() == "true"
        
        # Rate limiting
        self.rate_limit_enabled = self.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.rate_limit_requests = int(self.get("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window = int(self.get("RATE_LIMIT_WINDOW", "60"))
    
    def get_configured_tools(self) -> List[str]:
        """Return list of tools that have required configuration"""
        configured = []
        
        # Check each tool's requirements
        if self.hubspot_access_token or self.hubspot_api_key:
            configured.append("hubspot")
        
        if all([self.salesforce_username, self.salesforce_password, self.salesforce_security_token]):
            configured.append("salesforce")
        
        if self.pipedrive_api_token:
            configured.append("pipedrive")
        
        if all([self.calendly_client_id, self.calendly_client_secret, self.calendly_access_token, self.calendly_refresh_token]):
            configured.append("calendly")
        
        if os.path.exists(self.google_credentials_path):
            configured.extend(["google_calendar", "google_meet", "gmail", "google_sheets", "google_drive"])
        elif self.gmail_email and self.gmail_app_password:
            configured.append("gmail")
        
        if self.outreach_access_token:
            configured.append("outreach")
        
        if self.salesloft_api_key:
            configured.append("salesloft")
        
        if self.apollo_api_key:
            configured.append("apollo")
        
        if self.linkedin_access_token:
            configured.append("linkedin")
        
        if self.slack_bot_token or self.slack_webhook_url:
            configured.append("slack")
        
        if all([self.zoom_client_id, self.zoom_client_secret, self.zoom_account_id]):
            configured.append("zoom")
        
        if self.google_search_api_key and self.google_search_cse_id:
            configured.append("google_search")
        
        return configured
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate configuration and return status"""
        configured_tools = self.get_configured_tools()
        
        validation_result = {
            "valid": len(configured_tools) > 0,
            "configured_tools": configured_tools,
            "total_tools": 15,
            "missing_tools": [],
            "warnings": []
        }
        
        all_tools = [
            "hubspot", "salesforce", "pipedrive", "calendly", "google_calendar",
            "google_meet", "gmail", "google_sheets", "google_drive", "outreach",
            "salesloft", "apollo", "linkedin", "slack", "zoom"
        ]
        
        validation_result["missing_tools"] = [
            tool for tool in all_tools if tool not in configured_tools
        ]
        
        # Add warnings for common issues
        if not os.path.exists(self.google_credentials_path):
            validation_result["warnings"].append(
                f"Google credentials file not found: {self.google_credentials_path}"
            )
        
        if not any([self.hubspot_access_token, self.hubspot_api_key]):
            validation_result["warnings"].append("HubSpot not configured")
        
        return validation_result

# Global settings instance
settings = Settings()