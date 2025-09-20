"""Shared Google OAuth authentication manager
Handles authentication for all Google services (Calendar, Drive, Sheets, Gmail, Meet)
with automatic token refresh for production environments
"""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, Optional, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.external_account_authorized_user import Credentials as ExternalCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GoogleAuthManager:
    """Manages Google OAuth authentication for all Google services with automatic refresh"""

    def __init__(self, settings):
        self.settings = settings
        self.credentials: Union[Credentials, ExternalCredentials, None] = None
        self.services: dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._refresh_task = None
        self._refresh_interval = 1800  # 30 minutes in seconds
        self._min_token_lifetime = 300  # 5 minutes in seconds

    async def initialize(self):
        """Initialize Google authentication"""
        try:
            # Load existing credentials
            await self._load_credentials()

            # Try to refresh if needed
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    await self._refresh_credentials()
                except Exception as e:
                    logger.warning(f"Could not refresh credentials: {e}")
                    self.credentials = None

            # Check if we have valid credentials
            if not self.credentials or not self.credentials.valid:
                logger.warning("No valid Google credentials available.")
                logger.info("Google tools will use limited functionality or be disabled.")
                # Don't return False immediately, try to authenticate if in development
                if self._is_development_mode():
                    try:
                        await self._authenticate()
                    except Exception as e:
                        logger.warning(f"Could not authenticate: {e}")
                        return False
                else:
                    return False

            # Build commonly used services
            await self._build_services()

            # Start automatic token refresh monitoring in production
            if not self._is_development_mode():
                self._start_background_refresh()

            logger.info("Google authentication initialized successfully")
            return True

        except Exception as e:
            logger.warning(f"Google authentication failed: {e}. Google tools will be disabled.")
            return False

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

    async def _refresh_credentials(self):
        """Refresh expired credentials using refresh token"""
        if not self.credentials or not self.credentials.refresh_token:
            raise Exception("No refresh token available")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self.credentials.refresh,
            Request()
        )

        # Save refreshed credentials
        await self._save_credentials()
        logger.info("Successfully refreshed Google credentials")

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
        if self.credentials:
            with open(token_path, "w") as token:
                token.write(self.credentials.to_json())

    async def _build_services(self):
        """Build Google API service objects"""
        if not self.credentials:
            raise ValueError("No valid credentials available")

        try:
            loop = asyncio.get_event_loop()

            # Build services for each API
            services_to_build = [
                ("calendar", "v3"),
                ("drive", "v3"),
                ("sheets", "v4"),
                ("gmail", "v1")
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
        # Stop background refresh task
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        if self.executor:
            self.executor.shutdown(wait=True)

        self.services.clear()
        logger.info("Google auth manager cleaned up")

    def _is_development_mode(self) -> bool:
        """Check if running in development mode"""
        return os.getenv("ENVIRONMENT", "").lower() in ["dev", "development", "local"]

    def _start_background_refresh(self):
        """Start background token refresh monitoring"""
        if not self._refresh_task:
            self._refresh_task = asyncio.create_task(self._background_refresh_loop())
            logger.info("Started automatic token refresh monitoring")

    async def _background_refresh_loop(self):
        """Background loop to automatically refresh tokens before expiry"""
        while True:
            try:
                await asyncio.sleep(self._refresh_interval)

                if self.credentials and self._should_refresh_token():
                    logger.info("Automatically refreshing Google token before expiry")
                    await self._refresh_credentials()

                    # Rebuild services with new credentials
                    await self._build_services()
                    logger.info("Google services rebuilt with refreshed credentials")

            except asyncio.CancelledError:
                logger.info("Background token refresh stopped")
                break
            except Exception as e:
                logger.error(f"Error in background token refresh: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    def _should_refresh_token(self) -> bool:
        """Check if token should be refreshed"""
        if not self.credentials or not self.credentials.expiry:
            return False

        # Refresh if token expires within the minimum lifetime threshold
        time_until_expiry = self.credentials.expiry - datetime.utcnow()
        return time_until_expiry.total_seconds() < self._min_token_lifetime

    async def ensure_valid_credentials(self):
        """Ensure credentials are valid, refresh if needed (for production API calls)"""
        if not self.credentials:
            raise ValueError("No credentials available")

        if self._should_refresh_token():
            await self._refresh_credentials()
            # Rebuild services if needed
            if not self.services:
                await self._build_services()

        return self.credentials.valid
