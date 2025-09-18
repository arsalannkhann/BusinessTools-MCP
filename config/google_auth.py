"""Shared Google OAuth authentication manager
Handles authentication for all Google services (Calendar, Drive, Sheets, Gmail, Meet)
"""

import os
import json
import logging
from typing import Optional, List, Any, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class GoogleAuthManager:
    """Manages Google OAuth authentication for all Google services"""
    
    def __init__(self, settings):
        self.settings = settings
        self.credentials: Optional[Credentials] = None
        self.services: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def initialize(self):
        """Initialize Google authentication"""
        try:
            # Load credentials
            await self._load_credentials()
            
            if not self.credentials or not self.credentials.valid:
                await self._authenticate()
            
            # Build commonly used services
            await self._build_services()
            
            logger.info("Google authentication initialized successfully")
            
        except Exception as e:
            logger.error(f"Google authentication failed: {e}")
            raise
    
    async def _load_credentials(self):
        """Load existing credentials from token file"""
        token_path = self.settings.google_token_path
        
        if os.path.exists(token_path):
            try:
                loop = asyncio.get_event_loop()
                self.credentials = await loop.run_in_executor(
                    self.executor,
                    Credentials.from_authorized_user_file,
                    token_path,
                    self.settings.google_scopes
                )
                logger.info("Loaded existing Google credentials")
            except Exception as e:
                logger.warning(f"Could not load existing credentials: {e}")
    
    async def _authenticate(self):
        """Perform OAuth authentication flow"""
        creds_path = self.settings.google_credentials_path
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Google credentials file not found: {creds_path}")
        
        # Refresh existing credentials if possible
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.executor,
                    self.credentials.refresh,
                    Request()
                )
                logger.info("Refreshed Google credentials")
            except Exception as e:
                logger.warning(f"Could not refresh credentials: {e}")
                self.credentials = None
        
        # Perform new authentication if needed
        if not self.credentials or not self.credentials.valid:
            loop = asyncio.get_event_loop()
            
            flow = await loop.run_in_executor(
                self.executor,
                InstalledAppFlow.from_client_secrets_file,
                creds_path,
                self.settings.google_scopes
            )
            
            # For production, you might want to use a different flow
            # This is suitable for development/testing
            port = self.settings.server_port
            self.credentials = await loop.run_in_executor(
                self.executor,
                lambda: flow.run_local_server(port=port)
            )
            
            # Save credentials
            await self._save_credentials()
            logger.info("Completed Google OAuth authentication")
    
    async def _save_credentials(self):
        """Save credentials to token file"""
        if not self.credentials:
            return
        
        try:
            token_path = self.settings.google_token_path
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                self.executor,
                self._write_credentials_file,
                token_path
            )
            
            logger.info(f"Saved Google credentials to {token_path}")
            
        except Exception as e:
            logger.error(f"Could not save credentials: {e}")
    
    def _write_credentials_file(self, token_path: str):
        """Synchronous credentials file writing"""
        with open(token_path, 'w') as token:
            token.write(self.credentials.to_json())
    
    async def _build_services(self):
        """Build Google API service objects"""
        if not self.credentials:
            raise ValueError("No valid credentials available")
        
        try:
            loop = asyncio.get_event_loop()
            
            # Build services for each API
            services_to_build = [
                ('calendar', 'v3'),
                ('drive', 'v3'),
                ('sheets', 'v4'),
                ('gmail', 'v1')
            ]
            
            for service_name, version in services_to_build:
                try:
                    service = await loop.run_in_executor(
                        self.executor,
                        lambda: build(service_name, version, credentials=self.credentials)
                    )
                    self.services[service_name] = service
                    logger.debug(f"Built {service_name} service")
                    
                except Exception as e:
                    logger.warning(f"Could not build {service_name} service: {e}")
            
            logger.info(f"Built {len(self.services)} Google services")
            
        except Exception as e:
            logger.error(f"Failed to build Google services: {e}")
            raise
    
    def get_service(self, service_name: str):
        """Get a Google API service"""
        if service_name not in self.services:
            raise ValueError(f"Service {service_name} not available")
        return self.services[service_name]
    
    def is_authenticated(self) -> bool:
        """Check if authentication is valid"""
        return self.credentials is not None and self.credentials.valid
    
    async def refresh_if_needed(self):
        """Refresh credentials if needed"""
        if not self.credentials:
            return False
        
        if self.credentials.expired and self.credentials.refresh_token:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.executor,
                    self.credentials.refresh,
                    Request()
                )
                await self._save_credentials()
                return True
            except Exception as e:
                logger.error(f"Could not refresh credentials: {e}")
                return False
        
        return self.credentials.valid
    
    async def cleanup(self):
        """Clean up resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
        
        self.services.clear()
        logger.info("Google auth manager cleaned up")