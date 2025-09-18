"""
Pytest configuration and fixtures for Sales MCP Server tests
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import aiohttp
from config.settings import Settings
from config.google_auth import GoogleAuthManager

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = MagicMock(spec=Settings)
    
    # Google settings
    settings.google_credentials_path = "test_credentials.json"
    settings.google_token_path = "test_token.json"
    settings.google_scopes = ["https://www.googleapis.com/auth/calendar"]
    
    # Gmail settings
    settings.gmail_email = "test@example.com"
    settings.gmail_app_password = "test_password"
    
    # CRM settings
    settings.hubspot_access_token = "test_hubspot_token"
    settings.salesforce_username = "test@salesforce.com"
    settings.salesforce_password = "test_password"
    settings.salesforce_security_token = "test_token"
    settings.pipedrive_api_token = "test_pipedrive_token"
    settings.pipedrive_domain = "test-domain"
    
    # Other service settings
    settings.calendly_access_token = "test_calendly_token"
    settings.outreach_access_token = "test_outreach_token"
    settings.salesloft_api_key = "test_salesloft_key"
    settings.apollo_api_key = "test_apollo_key"
    settings.linkedin_access_token = "test_linkedin_token"
    settings.slack_bot_token = "test_slack_token"
    settings.zoom_api_key = "test_zoom_key"
    settings.zoom_api_secret = "test_zoom_secret"
    
    return settings

@pytest.fixture
def mock_google_auth():
    """Mock Google auth manager"""
    auth = AsyncMock(spec=GoogleAuthManager)
    auth.is_authenticated.return_value = True
    auth.get_service.return_value = MagicMock()
    return auth

@pytest.fixture
async def mock_http_session():
    """Mock aiohttp session"""
    session = AsyncMock(spec=aiohttp.ClientSession)
    
    # Mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"success": True, "data": {}}
    mock_response.text.return_value = "Success"
    
    # Mock session methods
    session.get.return_value.__aenter__.return_value = mock_response
    session.post.return_value.__aenter__.return_value = mock_response
    session.put.return_value.__aenter__.return_value = mock_response
    session.patch.return_value.__aenter__.return_value = mock_response
    session.delete.return_value.__aenter__.return_value = mock_response
    
    return session

@pytest.fixture
def sample_contact_data():
    """Sample contact data for testing"""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "company": "Test Company",
        "title": "Sales Manager",
        "phone": "+1234567890"
    }

@pytest.fixture
def sample_event_data():
    """Sample calendar event data for testing"""
    return {
        "summary": "Test Meeting",
        "description": "Test meeting description",
        "start": "2024-02-01T10:00:00Z",
        "end": "2024-02-01T11:00:00Z",
        "attendees": ["test@example.com"],
        "location": "Conference Room A"
    }

@pytest.fixture
def sample_email_data():
    """Sample email data for testing"""
    return {
        "to": ["recipient@example.com"],
        "subject": "Test Subject",
        "body": "Test email body",
        "from": "sender@example.com"
    }