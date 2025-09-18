"""
Calendly helper functions for token management and OAuth operations
Provides automatic token refresh and environment file management
"""

import os
import json
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class CalendlyTokenManager:
    """Manages Calendly OAuth tokens with automatic refresh"""
    
    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.base_url = "https://auth.calendly.com"
        self.api_url = "https://api.calendly.com"
        
    def load_credentials(self) -> bool:
        """Load credentials from environment variables"""
        self.client_id = os.getenv('CALENDLY_CLIENT_ID')
        self.client_secret = os.getenv('CALENDLY_CLIENT_SECRET')
        self.access_token = os.getenv('CALENDLY_ACCESS_TOKEN')
        self.refresh_token = os.getenv('CALENDLY_REFRESH_TOKEN')
        
        # Check if we have minimum required credentials
        if not self.access_token:
            logger.warning("No Calendly access token found")
            return False
            
        return True
    
    def _calculate_token_expiry(self, expires_in: int) -> datetime:
        """Calculate when the token will expire"""
        return datetime.utcnow() + timedelta(seconds=expires_in - 300)  # 5 min buffer
    
    def is_token_expired(self) -> bool:
        """Check if the current token is expired or will expire soon"""
        if not self.token_expires_at:
            # If we don't know when it expires, assume it needs refresh
            return True
        return datetime.utcnow() >= self.token_expires_at
    
    async def refresh_access_token(self) -> Optional[Dict[str, Any]]:
        """Refresh the access token using the refresh token"""
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            logger.error("Missing OAuth credentials for token refresh")
            return None
        
        refresh_data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/oauth/token",
                    data=refresh_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                ) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        
                        # Update instance variables
                        self.access_token = token_data['access_token']
                        if 'refresh_token' in token_data:
                            self.refresh_token = token_data['refresh_token']
                        
                        # Calculate expiry time
                        expires_in = token_data.get('expires_in', 7200)  # Default 2 hours
                        self.token_expires_at = self._calculate_token_expiry(expires_in)
                        
                        logger.info("Calendly access token refreshed successfully")
                        return token_data
                    else:
                        error_text = await response.text()
                        logger.error(f"Token refresh failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error refreshing Calendly token: {e}")
            return None
    
    async def validate_token(self) -> bool:
        """Validate the current access token by making a test API call"""
        if not self.access_token:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {self.access_token}'}
                async with session.get(f"{self.api_url}/users/me", headers=headers) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Error validating Calendly token: {e}")
            return False
    
    async def ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token, refreshing if necessary"""
        # First, try to validate current token
        if self.access_token:
            if await self.validate_token():
                logger.debug("Current Calendly token is valid")
                return True
        
        # Token is invalid, try to refresh if we have refresh credentials
        if self.refresh_token and self.client_id and self.client_secret:
            logger.info("Calendly token invalid, attempting refresh...")
            token_data = await self.refresh_access_token()
            if token_data:
                # Update environment variables
                await update_env_file({
                    'CALENDLY_ACCESS_TOKEN': self.access_token,
                    'CALENDLY_REFRESH_TOKEN': self.refresh_token
                })
                return True
        
        # If no refresh token available but we have a token, use it if valid
        if self.access_token and await self.validate_token():
            logger.info("Using existing Calendly access token (no refresh available)")
            return True
        
        logger.error("Unable to ensure valid Calendly token")
        return False

# Global token manager instance
_token_manager = CalendlyTokenManager()

async def refresh_token_if_needed(
    client_id: str, 
    client_secret: str, 
    refresh_token: str,
    base_url: str = "https://auth.calendly.com"
) -> Optional[Dict[str, Any]]:
    """Refresh Calendly access token if needed"""
    global _token_manager
    
    # Update token manager with provided credentials
    _token_manager.client_id = client_id
    _token_manager.client_secret = client_secret
    _token_manager.refresh_token = refresh_token
    
    return await _token_manager.refresh_access_token()

async def get_valid_access_token() -> Optional[str]:
    """Get a valid access token, refreshing if necessary"""
    global _token_manager
    
    if not _token_manager.load_credentials():
        return None
    
    if await _token_manager.ensure_valid_token():
        return _token_manager.access_token
    
    return None

async def update_env_file(token_data: Dict[str, Any]) -> None:
    """Update environment file with new token data"""
    env_file_path = Path('.env')
    
    if not env_file_path.exists():
        logger.warning("No .env file found, creating one...")
        env_file_path.touch()
    
    try:
        # Read current .env file
        env_content = ""
        if env_file_path.exists():
            with open(env_file_path, 'r') as f:
                env_content = f.read()
        
        # Update or add each token
        for key, value in token_data.items():
            if not value:
                continue
                
            env_var_pattern = rf'^{re.escape(key)}=.*$'
            env_var_line = f'{key}={value}'
            
            if re.search(env_var_pattern, env_content, re.MULTILINE):
                # Update existing variable
                env_content = re.sub(env_var_pattern, env_var_line, env_content, flags=re.MULTILINE)
            else:
                # Add new variable
                if env_content and not env_content.endswith('\n'):
                    env_content += '\n'
                env_content += f'{env_var_line}\n'
        
        # Write back to file
        with open(env_file_path, 'w') as f:
            f.write(env_content)
        
        # Update current process environment
        for key, value in token_data.items():
            if value:
                os.environ[key] = str(value)
        
        logger.info(f"Updated .env file with {len(token_data)} variables")
        
    except Exception as e:
        logger.error(f"Error updating .env file: {e}")

async def create_calendly_oauth_url(
    client_id: str, 
    redirect_uri: str, 
    state: Optional[str] = None
) -> str:
    """Create Calendly OAuth authorization URL"""
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri
    }
    
    if state:
        params['state'] = state
    
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return f"https://auth.calendly.com/oauth/authorize?{query_string}"

async def exchange_code_for_tokens(
    client_id: str,
    client_secret: str, 
    redirect_uri: str,
    code: str
) -> Optional[Dict[str, Any]]:
    """Exchange authorization code for access and refresh tokens"""
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://auth.calendly.com/oauth/token",
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                if response.status == 200:
                    tokens = await response.json()
                    logger.info("Successfully exchanged code for Calendly tokens")
                    return tokens
                else:
                    error_text = await response.text()
                    logger.error(f"Token exchange failed: {response.status} - {error_text}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error exchanging code for tokens: {e}")
        return None

class CalendlyAPIClient:
    """Enhanced Calendly API client with automatic token refresh"""
    
    def __init__(self, token_manager: Optional[CalendlyTokenManager] = None):
        self.token_manager = token_manager or _token_manager
        self.base_url = "https://api.calendly.com"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with valid access token"""
        if not await self.token_manager.ensure_valid_token():
            raise ValueError("Unable to obtain valid Calendly access token")
        
        return {
            'Authorization': f'Bearer {self.token_manager.access_token}',
            'Content-Type': 'application/json'
        }
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Tuple[bool, Any]:
        """Make authenticated GET request"""
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' context manager.")
        
        try:
            headers = await self._get_headers()
            async with self.session.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                params=params or {}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, data
                else:
                    error_text = await response.text()
                    logger.error(f"GET {endpoint} failed: {response.status} - {error_text}")
                    return False, error_text
                    
        except Exception as e:
            logger.error(f"Error making GET request to {endpoint}: {e}")
            return False, str(e)
    
    async def post(self, endpoint: str, data: Optional[Dict] = None) -> Tuple[bool, Any]:
        """Make authenticated POST request"""
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' context manager.")
        
        try:
            headers = await self._get_headers()
            async with self.session.post(
                f"{self.base_url}{endpoint}",
                headers=headers,
                json=data or {}
            ) as response:
                if response.status in [200, 201]:
                    response_data = await response.json()
                    return True, response_data
                else:
                    error_text = await response.text()
                    logger.error(f"POST {endpoint} failed: {response.status} - {error_text}")
                    return False, error_text
                    
        except Exception as e:
            logger.error(f"Error making POST request to {endpoint}: {e}")
            return False, str(e)
    
    async def delete(self, endpoint: str) -> Tuple[bool, Any]:
        """Make authenticated DELETE request"""
        if not self.session:
            raise RuntimeError("Client session not initialized. Use 'async with' context manager.")
        
        try:
            headers = await self._get_headers()
            async with self.session.delete(
                f"{self.base_url}{endpoint}",
                headers=headers
            ) as response:
                if response.status in [200, 204]:
                    return True, "Deleted successfully"
                else:
                    error_text = await response.text()
                    logger.error(f"DELETE {endpoint} failed: {response.status} - {error_text}")
                    return False, error_text
                    
        except Exception as e:
            logger.error(f"Error making DELETE request to {endpoint}: {e}")
            return False, str(e)

# Helper functions for backward compatibility
async def initialize_calendly_helper():
    """Initialize the Calendly helper with environment credentials"""
    global _token_manager
    _token_manager.load_credentials()
    logger.info("Calendly helper initialized")

async def get_calendly_client() -> CalendlyAPIClient:
    """Get an authenticated Calendly API client"""
    return CalendlyAPIClient(_token_manager)
