"""
Tests for configuration management
"""

import json
import os
from unittest.mock import mock_open, patch

from config.settings import Settings


class TestSettings:
    """Test settings configuration"""

    def test_settings_initialization(self):
        """Test settings initialization"""
        with patch.dict(os.environ, {
            "HUBSPOT_ACCESS_TOKEN": "test_token",
            "SALESFORCE_USERNAME": "test@example.com"
        }):
            settings = Settings()
            assert settings.hubspot_access_token == "test_token"
            assert settings.salesforce_username == "test@example.com"

    def test_json_settings_loading(self):
        """Test loading settings from JSON file"""
        json_data = {
            "hubspot": {
                "access_token": "json_token"
            }
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(json_data))):
            with patch("os.path.exists", return_value=True):
                settings = Settings()
                # Should load from JSON when env var not set
                assert settings.get("access_token", section="hubspot") == "json_token"

    def test_get_configured_tools(self):
        """Test configured tools detection"""
        with patch.dict(os.environ, {
            "HUBSPOT_ACCESS_TOKEN": "test_token",
            "SLACK_BOT_TOKEN": "test_slack_token"
        }):
            settings = Settings()
            configured_tools = settings.get_configured_tools()
            assert "hubspot" in configured_tools
            assert "slack" in configured_tools

    def test_validate_configuration(self):
        """Test configuration validation"""
        with patch.dict(os.environ, {"HUBSPOT_ACCESS_TOKEN": "test_token"}):
            settings = Settings()
            validation = settings.validate_configuration()
            assert validation["valid"] is True
            assert "hubspot" in validation["configured_tools"]
            assert len(validation["missing_tools"]) > 0
