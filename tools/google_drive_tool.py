"""
Google Drive integration tool for file management, sharing, and collaboration
Provides comprehensive file operations and document management capabilities
"""

import asyncio
import io
import logging
import mimetypes
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from mcp import types

from .base import SalesTool, ToolResult

logger = logging.getLogger(__name__)

def validate_required_params(params: dict[str, Any], required: list[str]) -> str | None:
    """Validate required parameters"""
    missing = [param for param in required if param not in params or params[param] is None]
    if missing:
        return f"Missing required parameters: {', '.join(missing)}"
    return None

class GoogleDriveTool(SalesTool):
    """Google Drive file management and collaboration tool"""

    def __init__(self):
        super().__init__("google_drive", "Google Drive file management and sharing")
        self.drive_service = None
        self.google_auth = None
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Google Drive tool"""
        if not google_auth or not google_auth.is_authenticated():
            self.logger.warning("Google authentication not available")
            return False

        try:
            self.google_auth = google_auth
            self.drive_service = google_auth.get_service("drive")

            if not self.drive_service:
                self.logger.error("Failed to get Google Drive service")
                return False

            self.logger.info("Google Drive tool initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Google Drive tool: {e}")
            return False

    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return self.drive_service is not None

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """Execute Google Drive action"""
        if not self.drive_service:
            return self._create_error_result("Google Drive tool not initialized")

        try:
            # Refresh auth if needed
            await self.google_auth.refresh_if_needed()

            # File Operations
            if action == "list_files":
                return await self._list_files(params)
            if action == "get_file":
                return await self._get_file(params)
            if action == "upload_file":
                return await self._upload_file(params)
            if action == "download_file":
                return await self._download_file(params)
            if action == "delete_file":
                return await self._delete_file(params)
            if action == "copy_file":
                return await self._copy_file(params)
            if action == "move_file":
                return await self._move_file(params)

            # Folder Operations
            if action == "create_folder":
                return await self._create_folder(params)
            if action == "list_folder_contents":
                return await self._list_folder_contents(params)

            # Sharing and Permissions
            if action == "share_file":
                return await self._share_file(params)
            if action == "update_permissions":
                return await self._update_permissions(params)
            if action == "list_permissions":
                return await self._list_permissions(params)
            if action == "remove_permission":
                return await self._remove_permission(params)

            # File Metadata and Updates
            if action == "update_file_metadata":
                return await self._update_file_metadata(params)
            if action == "rename_file":
                return await self._rename_file(params)
            if action == "add_comment":
                return await self._add_comment(params)
            if action == "list_comments":
                return await self._list_comments(params)

            # Search and Organization
            if action == "search_files":
                return await self._search_files(params)
            if action == "get_file_revisions":
                return await self._get_file_revisions(params)
            if action == "restore_revision":
                return await self._restore_revision(params)

            # Bulk Operations
            if action == "batch_delete":
                return await self._batch_delete(params)
            if action == "batch_move":
                return await self._batch_move(params)
            if action == "batch_share":
                return await self._batch_share(params)

            # Drive Info
            if action == "get_drive_info":
                return await self._get_drive_info(params)
            if action == "get_quota" or action == "get_storage_info":
                return await self._get_quota(params)

            return self._create_error_result(f"Unknown action: {action}")

        except Exception as e:
            self.logger.error(f"Error executing Google Drive action {action}: {e}")
            return self._create_error_result(f"Action failed: {e!s}")

    async def _list_files(self, params: dict[str, Any]) -> ToolResult:
        """List files in Drive"""
        try:
            query_params = {
                "pageSize": params.get("page_size", 100),
                "fields": "nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, owners, shared, parents, webViewLink)",
                "orderBy": params.get("order_by", "modifiedTime desc")
            }

            # Add query filter if provided
            query_filter = params.get("query")
            if query_filter:
                query_params["q"] = query_filter
            elif params.get("folder_id"):
                query_params["q"] = f"'{params['folder_id']}' in parents"
            elif params.get("mime_type"):
                query_params["q"] = f"mimeType='{params['mime_type']}'"

            # Add page token for pagination
            if params.get("page_token"):
                query_params["pageToken"] = params["page_token"]

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().list(**query_params).execute()
            )

            return self._create_success_result({
                "files": result.get("files", []),
                "next_page_token": result.get("nextPageToken"),
                "total_files": len(result.get("files", []))
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to list files: {e}")

    async def _get_file(self, params: dict[str, Any]) -> ToolResult:
        """Get file metadata"""
        error = validate_required_params(params, ["file_id"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]
            fields = params.get("fields", "id, name, mimeType, size, createdTime, modifiedTime, owners, shared, parents, webViewLink, description, starred, trashed")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().get(fileId=file_id, fields=fields).execute()
            )

            return self._create_success_result(result)

        except HttpError as e:
            return self._create_error_result(f"Failed to get file: {e}")

    async def _upload_file(self, params: dict[str, Any]) -> ToolResult:
        """Upload file to Drive"""
        self.logger.info(f"Starting file upload with params: {list(params.keys())}")

        error = validate_required_params(params, ["name"])
        if error:
            self.logger.error(f"Missing required parameters: {error}")
            return self._create_error_result(error)

        if "content" not in params and "file_path" not in params:
            self.logger.error("No content or file_path provided")
            return self._create_error_result("Must provide either 'content' or 'file_path'")

        try:
            # Check if drive service is available
            if not self.drive_service:
                self.logger.error("Google Drive service not initialized")
                return self._create_error_result("Google Drive service not initialized")

            file_name = params["name"]
            mime_type = params.get("mime_type")

            self.logger.info(f"Uploading file: {file_name}, mime_type: {mime_type}")

            # Determine MIME type if not provided
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(file_name)
                if not mime_type:
                    mime_type = "text/plain" if params.get("content") else "application/octet-stream"
                self.logger.info(f"Auto-detected mime_type: {mime_type}")

            # File metadata
            file_metadata = {
                "name": file_name,
                "description": params.get("description", ""),
            }

            # Handle parent folder
            parent_folder_id = params.get("parent_folder_id")
            if parent_folder_id:
                file_metadata["parents"] = [parent_folder_id]
                self.logger.info(f"Setting parent folder: {parent_folder_id}")

            # Handle content
            if "content" in params:
                # Upload from string content
                content = params["content"]
                if isinstance(content, str):
                    content_bytes = content.encode("utf-8")
                else:
                    content_bytes = content

                self.logger.info(f"Content size: {len(content_bytes)} bytes")

                media_body = MediaIoBaseUpload(
                    io.BytesIO(content_bytes),
                    mimetype=mime_type,
                    resumable=False
                )
            else:
                # Upload from file path
                try:
                    with open(params["file_path"], "rb") as f:
                        content_bytes = f.read()

                    self.logger.info(f"File size: {len(content_bytes)} bytes")

                    media_body = MediaIoBaseUpload(
                        io.BytesIO(content_bytes),
                        mimetype=mime_type,
                        resumable=False
                    )
                except FileNotFoundError:
                    self.logger.error(f"File not found: {params['file_path']}")
                    return self._create_error_result(f"File not found: {params['file_path']}")
                except Exception as file_error:
                    self.logger.error(f"Error reading file: {file_error!s}")
                    return self._create_error_result(f"Error reading file: {file_error!s}")

            # Refresh auth if needed
            if self.google_auth:
                await self.google_auth.refresh_if_needed()

            self.logger.info("Executing drive service create request")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media_body,
                    fields="id, name, webViewLink, size, mimeType, createdTime"
                ).execute()
            )

            self.logger.info(f"Upload successful: {result.get('id', 'unknown')}")

            return self._create_success_result({
                "file_id": result["id"],
                "name": result["name"],
                "web_view_link": result.get("webViewLink"),
                "download_link": result.get("webViewLink"),  # Use webViewLink instead
                "size": result.get("size"),
                "mime_type": result.get("mimeType"),
                "created_time": result.get("createdTime"),
                "uploaded": True,
                "message": f"Successfully uploaded '{file_name}' to Google Drive"
            })

        except HttpError as e:
            error_details = f"HTTP {e.resp.status}: {e.content.decode() if e.content else 'Unknown error'}"
            self.logger.error(f"HTTP Error during upload: {error_details}")
            return self._create_error_result(f"Failed to upload file: {error_details}")
        except Exception as e:
            self.logger.error(f"Unexpected error during upload: {e!s}")
            return self._create_error_result(f"Failed to upload file: {e!s}")

    async def _download_file(self, params: dict[str, Any]) -> ToolResult:
        """Download file from Drive"""
        error = validate_required_params(params, ["file_id"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]

            # Get file metadata first
            loop = asyncio.get_event_loop()
            file_info = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().get(fileId=file_id, fields="name, mimeType, size").execute()
            )

            # Download file content
            request = self.drive_service.files().get_media(fileId=file_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)

            done = False
            while not done:
                status, done = await loop.run_in_executor(
                    self.executor,
                    downloader.next_chunk
                )

            file_content = file_io.getvalue()

            # Save to file if path provided
            if params.get("save_path"):
                with open(params["save_path"], "wb") as f:
                    f.write(file_content)

                return self._create_success_result({
                    "file_info": file_info,
                    "saved_to": params["save_path"],
                    "size": len(file_content)
                })
            # Return content (be careful with large files)
            if len(file_content) > 1024 * 1024:  # 1MB limit
                return self._create_success_result({
                    "file_info": file_info,
                    "message": "File too large to return content directly. Use save_path parameter.",
                    "size": len(file_content)
                })

            return self._create_success_result({
                "file_info": file_info,
                "content": file_content.decode("utf-8") if file_info.get("mimeType", "").startswith("text/") else None,
                "raw_content": file_content if len(file_content) <= 10240 else None,  # 10KB limit for raw
                "size": len(file_content)
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to download file: {e}")

    async def _delete_file(self, params: dict[str, Any]) -> ToolResult:
        """Delete file from Drive"""
        error = validate_required_params(params, ["file_id"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().delete(fileId=file_id).execute()
            )

            return self._create_success_result({
                "deleted": True,
                "file_id": file_id
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to delete file: {e}")

    async def _copy_file(self, params: dict[str, Any]) -> ToolResult:
        """Copy file in Drive"""
        error = validate_required_params(params, ["file_id", "name"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]
            copy_metadata = {
                "name": params["name"],
                "description": params.get("description", ""),
                "parents": params.get("parent_ids", [])
            }

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().copy(
                    fileId=file_id,
                    body=copy_metadata,
                    fields="id, name, webViewLink"
                ).execute()
            )

            return self._create_success_result({
                "copied_file": result,
                "original_id": file_id
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to copy file: {e}")

    async def _move_file(self, params: dict[str, Any]) -> ToolResult:
        """Move file to different folder"""
        error = validate_required_params(params, ["file_id", "new_parent_id"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]
            new_parent_id = params["new_parent_id"]

            # Get current parents
            loop = asyncio.get_event_loop()
            file_info = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().get(fileId=file_id, fields="parents").execute()
            )

            previous_parents = ",".join(file_info.get("parents", []))

            # Move file
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().update(
                    fileId=file_id,
                    addParents=new_parent_id,
                    removeParents=previous_parents,
                    fields="id, parents"
                ).execute()
            )

            return self._create_success_result({
                "moved": True,
                "file_id": file_id,
                "new_parents": result.get("parents", []),
                "previous_parents": previous_parents.split(",") if previous_parents else []
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to move file: {e}")

    async def _create_folder(self, params: dict[str, Any]) -> ToolResult:
        """Create new folder"""
        error = validate_required_params(params, ["name"])
        if error:
            return self._create_error_result(error)

        try:
            folder_metadata = {
                "name": params["name"],
                "mimeType": "application/vnd.google-apps.folder",
                "description": params.get("description", ""),
                "parents": params.get("parent_ids", [])
            }

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().create(
                    body=folder_metadata,
                    fields="id, name, webViewLink"
                ).execute()
            )

            return self._create_success_result({
                "folder": result,
                "created": True
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to create folder: {e}")

    async def _list_folder_contents(self, params: dict[str, Any]) -> ToolResult:
        """List contents of a specific folder"""
        error = validate_required_params(params, ["folder_id"])
        if error:
            return self._create_error_result(error)

        # Use list_files with folder filter
        params["query"] = f"'{params['folder_id']}' in parents"
        return await self._list_files(params)

    async def _share_file(self, params: dict[str, Any]) -> ToolResult:
        """Share file with users or make public"""
        error = validate_required_params(params, ["file_id", "role"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]
            role = params["role"]  # owner, organizer, fileOrganizer, writer, commenter, reader

            permission_data = {
                "role": role,
                "type": params.get("type", "user")  # user, group, domain, anyone
            }

            if params.get("email_address"):
                permission_data["emailAddress"] = params["email_address"]

            if params.get("domain"):
                permission_data["domain"] = params["domain"]

            # Additional options
            if params.get("allow_file_discovery") is not None:
                permission_data["allowFileDiscovery"] = params["allow_file_discovery"]

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.permissions().create(
                    fileId=file_id,
                    body=permission_data,
                    sendNotificationEmail=params.get("send_notification", True),
                    emailMessage=params.get("email_message", ""),
                    fields="id, role, type, emailAddress"
                ).execute()
            )

            return self._create_success_result({
                "permission": result,
                "file_id": file_id,
                "shared": True
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to share file: {e}")

    async def _update_permissions(self, params: dict[str, Any]) -> ToolResult:
        """Update existing file permissions"""
        error = validate_required_params(params, ["file_id", "permission_id", "role"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]
            permission_id = params["permission_id"]

            permission_data = {
                "role": params["role"]
            }

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.permissions().update(
                    fileId=file_id,
                    permissionId=permission_id,
                    body=permission_data,
                    fields="id, role, type, emailAddress"
                ).execute()
            )

            return self._create_success_result({
                "permission": result,
                "updated": True
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to update permissions: {e}")

    async def _list_permissions(self, params: dict[str, Any]) -> ToolResult:
        """List file permissions"""
        error = validate_required_params(params, ["file_id"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.permissions().list(
                    fileId=file_id,
                    fields="permissions(id, role, type, emailAddress, displayName)"
                ).execute()
            )

            return self._create_success_result({
                "permissions": result.get("permissions", []),
                "file_id": file_id
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to list permissions: {e}")

    async def _remove_permission(self, params: dict[str, Any]) -> ToolResult:
        """Remove file permission"""
        error = validate_required_params(params, ["file_id", "permission_id"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]
            permission_id = params["permission_id"]

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.permissions().delete(
                    fileId=file_id,
                    permissionId=permission_id
                ).execute()
            )

            return self._create_success_result({
                "removed": True,
                "file_id": file_id,
                "permission_id": permission_id
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to remove permission: {e}")

    async def _update_file_metadata(self, params: dict[str, Any]) -> ToolResult:
        """Update file metadata"""
        error = validate_required_params(params, ["file_id"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]

            update_data = {}
            if "name" in params:
                update_data["name"] = params["name"]
            if "description" in params:
                update_data["description"] = params["description"]
            if "starred" in params:
                update_data["starred"] = params["starred"]

            if not update_data:
                return self._create_error_result("No metadata to update")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().update(
                    fileId=file_id,
                    body=update_data,
                    fields="id, name, description, starred, modifiedTime"
                ).execute()
            )

            return self._create_success_result({
                "file": result,
                "updated": True
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to update file metadata: {e}")

    async def _rename_file(self, params: dict[str, Any]) -> ToolResult:
        """Rename file"""
        error = validate_required_params(params, ["file_id", "new_name"])
        if error:
            return self._create_error_result(error)

        params["name"] = params["new_name"]
        return await self._update_file_metadata(params)

    async def _add_comment(self, params: dict[str, Any]) -> ToolResult:
        """Add comment to file"""
        error = validate_required_params(params, ["file_id", "content"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]

            comment_data = {
                "content": params["content"],
                "anchor": params.get("anchor")  # For specific text selection
            }

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.comments().create(
                    fileId=file_id,
                    body=comment_data,
                    fields="id, content, author, createdTime"
                ).execute()
            )

            return self._create_success_result({
                "comment": result,
                "file_id": file_id
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to add comment: {e}")

    async def _list_comments(self, params: dict[str, Any]) -> ToolResult:
        """List file comments"""
        error = validate_required_params(params, ["file_id"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.comments().list(
                    fileId=file_id,
                    fields="comments(id, content, author, createdTime, replies)",
                    pageSize=params.get("page_size", 100)
                ).execute()
            )

            return self._create_success_result({
                "comments": result.get("comments", []),
                "file_id": file_id,
                "total_comments": len(result.get("comments", []))
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to list comments: {e}")

    async def _search_files(self, params: dict[str, Any]) -> ToolResult:
        """Search files with advanced query"""
        search_terms = []

        # Build search query
        if params.get("name"):
            search_terms.append(f"name contains '{params['name']}'")

        if params.get("content"):
            search_terms.append(f"fullText contains '{params['content']}'")

        if params.get("mime_type"):
            search_terms.append(f"mimeType='{params['mime_type']}'")

        if params.get("owner"):
            search_terms.append(f"'{params['owner']}' in owners")

        if params.get("shared"):
            search_terms.append("sharedWithMe" if params["shared"] else "not sharedWithMe")

        if params.get("starred"):
            search_terms.append("starred" if params["starred"] else "not starred")

        if params.get("trashed") is not None:
            search_terms.append("trashed" if params["trashed"] else "not trashed")

        if params.get("modified_after"):
            search_terms.append(f"modifiedTime > '{params['modified_after']}'")

        if params.get("modified_before"):
            search_terms.append(f"modifiedTime < '{params['modified_before']}'")

        # Combine search terms
        query = " and ".join(search_terms) if search_terms else None

        # Use existing list_files method
        search_params = {
            "query": query,
            "page_size": params.get("page_size", 100),
            "order_by": params.get("order_by", "modifiedTime desc"),  # Use valid orderBy value
            "page_token": params.get("page_token")
        }

        return await self._list_files(search_params)

    async def _get_file_revisions(self, params: dict[str, Any]) -> ToolResult:
        """Get file revision history"""
        error = validate_required_params(params, ["file_id"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.revisions().list(
                    fileId=file_id,
                    fields="revisions(id, modifiedTime, size, originalFilename, lastModifyingUser)"
                ).execute()
            )

            return self._create_success_result({
                "revisions": result.get("revisions", []),
                "file_id": file_id
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to get file revisions: {e}")

    async def _restore_revision(self, params: dict[str, Any]) -> ToolResult:
        """Restore file to specific revision"""
        error = validate_required_params(params, ["file_id", "revision_id"])
        if error:
            return self._create_error_result(error)

        try:
            file_id = params["file_id"]
            revision_id = params["revision_id"]

            # Get revision content
            loop = asyncio.get_event_loop()
            request = self.drive_service.revisions().get_media(fileId=file_id, revisionId=revision_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)

            done = False
            while not done:
                status, done = await loop.run_in_executor(
                    self.executor,
                    downloader.next_chunk
                )

            # Upload as new version
            media_body = MediaIoBaseUpload(
                io.BytesIO(file_io.getvalue()),
                resumable=True
            )

            result = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.files().update(
                    fileId=file_id,
                    media_body=media_body,
                    fields="id, modifiedTime"
                ).execute()
            )

            return self._create_success_result({
                "restored": True,
                "file_id": file_id,
                "revision_id": revision_id,
                "new_modified_time": result.get("modifiedTime")
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to restore revision: {e}")

    async def _batch_delete(self, params: dict[str, Any]) -> ToolResult:
        """Delete multiple files"""
        error = validate_required_params(params, ["file_ids"])
        if error:
            return self._create_error_result(error)

        file_ids = params["file_ids"]
        results = []

        for file_id in file_ids:
            try:
                result = await self._delete_file({"file_id": file_id})
                results.append({
                    "file_id": file_id,
                    "success": result.success,
                    "error": result.error
                })
            except Exception as e:
                results.append({
                    "file_id": file_id,
                    "success": False,
                    "error": str(e)
                })

        successful = sum(1 for r in results if r["success"])

        return self._create_success_result({
            "batch_results": results,
            "total_files": len(file_ids),
            "successful": successful,
            "failed": len(file_ids) - successful
        })

    async def _batch_move(self, params: dict[str, Any]) -> ToolResult:
        """Move multiple files to new folder"""
        error = validate_required_params(params, ["file_ids", "new_parent_id"])
        if error:
            return self._create_error_result(error)

        file_ids = params["file_ids"]
        new_parent_id = params["new_parent_id"]
        results = []

        for file_id in file_ids:
            try:
                result = await self._move_file({
                    "file_id": file_id,
                    "new_parent_id": new_parent_id
                })
                results.append({
                    "file_id": file_id,
                    "success": result.success,
                    "error": result.error
                })
            except Exception as e:
                results.append({
                    "file_id": file_id,
                    "success": False,
                    "error": str(e)
                })

        successful = sum(1 for r in results if r["success"])

        return self._create_success_result({
            "batch_results": results,
            "total_files": len(file_ids),
            "successful": successful,
            "failed": len(file_ids) - successful,
            "new_parent_id": new_parent_id
        })

    async def _batch_share(self, params: dict[str, Any]) -> ToolResult:
        """Share multiple files with same permissions"""
        error = validate_required_params(params, ["file_ids", "role"])
        if error:
            return self._create_error_result(error)

        file_ids = params["file_ids"]
        results = []

        # Prepare sharing parameters
        share_params = {
            "role": params["role"],
            "type": params.get("type", "user"),
            "email_address": params.get("email_address"),
            "domain": params.get("domain"),
            "send_notification": params.get("send_notification", True),
            "email_message": params.get("email_message", "")
        }

        for file_id in file_ids:
            try:
                share_params["file_id"] = file_id
                result = await self._share_file(share_params)
                results.append({
                    "file_id": file_id,
                    "success": result.success,
                    "error": result.error,
                    "permission_id": result.data.get("permission", {}).get("id") if result.success else None
                })
            except Exception as e:
                results.append({
                    "file_id": file_id,
                    "success": False,
                    "error": str(e)
                })

        successful = sum(1 for r in results if r["success"])

        return self._create_success_result({
            "batch_results": results,
            "total_files": len(file_ids),
            "successful": successful,
            "failed": len(file_ids) - successful,
            "sharing_config": {
                "role": params["role"],
                "type": params.get("type", "user"),
                "email_address": params.get("email_address")
            }
        })

    async def _get_drive_info(self, params: dict[str, Any]) -> ToolResult:
        """Get Drive information"""
        try:
            loop = asyncio.get_event_loop()
            about_info = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.about().get(
                    fields="user, storageQuota, importFormats, exportFormats"
                ).execute()
            )

            return self._create_success_result({
                "drive_info": about_info,
                "user": about_info.get("user", {}),
                "storage_quota": about_info.get("storageQuota", {}),
                "import_formats": about_info.get("importFormats", {}),
                "export_formats": about_info.get("exportFormats", {})
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to get Drive info: {e}")

    async def _get_quota(self, params: dict[str, Any]) -> ToolResult:
        """Get storage quota information"""
        try:
            loop = asyncio.get_event_loop()
            about_info = await loop.run_in_executor(
                self.executor,
                lambda: self.drive_service.about().get(fields="storageQuota").execute()
            )

            quota = about_info.get("storageQuota", {})

            # Calculate usage percentages if limits are available
            usage_info = {}
            if quota.get("limit") and quota.get("usage"):
                total_limit = int(quota["limit"])
                total_usage = int(quota["usage"])
                usage_info["usage_percentage"] = (total_usage / total_limit) * 100
                usage_info["remaining"] = total_limit - total_usage

            return self._create_success_result({
                "storage_quota": quota,
                "usage_analysis": usage_info
            })

        except HttpError as e:
            return self._create_error_result(f"Failed to get quota info: {e}")

    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition"""
        return types.Tool(
            name="google_drive",
            description="Google Drive file management, sharing, and collaboration operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            # File Operations
                            "list_files", "get_file", "upload_file", "download_file",
                            "delete_file", "copy_file", "move_file", "rename_file",

                            # Folder Operations
                            "create_folder", "list_folder_contents",

                            # Sharing and Permissions
                            "share_file", "update_permissions", "list_permissions",
                            "remove_permission",

                            # Metadata and Comments
                            "update_file_metadata", "add_comment", "list_comments",

                            # Search and Revisions
                            "search_files", "get_file_revisions", "restore_revision",

                            # Bulk Operations
                            "batch_delete", "batch_move", "batch_share",

                            # Drive Info
                            "get_drive_info", "get_quota"
                        ],
                        "description": "The action to perform"
                    },

                    # File identifiers
                    "file_id": {"type": "string", "description": "Google Drive file ID"},
                    "file_ids": {"type": "array", "items": {"type": "string"}, "description": "Array of file IDs for batch operations"},
                    "folder_id": {"type": "string", "description": "Folder ID to list contents"},
                    "parent_ids": {"type": "array", "items": {"type": "string"}, "description": "Parent folder IDs"},
                    "new_parent_id": {"type": "string", "description": "New parent folder ID for moving files"},

                    # File metadata
                    "name": {"type": "string", "description": "File or folder name"},
                    "new_name": {"type": "string", "description": "New name for renaming"},
                    "description": {"type": "string", "description": "File description"},
                    "starred": {"type": "boolean", "description": "Star/unstar file"},

                    # File content
                    "content": {"type": "string", "description": "File content for upload"},
                    "file_path": {"type": "string", "description": "Local file path for upload"},
                    "save_path": {"type": "string", "description": "Local save path for download"},
                    "mime_type": {"type": "string", "description": "MIME type for file upload"},

                    # Permissions and sharing
                    "role": {"type": "string", "enum": ["owner", "organizer", "fileOrganizer", "writer", "commenter", "reader"], "description": "Permission role"},
                    "type": {"type": "string", "enum": ["user", "group", "domain", "anyone"], "description": "Permission type"},
                    "email_address": {"type": "string", "description": "Email address for sharing"},
                    "domain": {"type": "string", "description": "Domain for sharing"},
                    "permission_id": {"type": "string", "description": "Permission ID"},
                    "send_notification": {"type": "boolean", "description": "Send email notification", "default": True},
                    "email_message": {"type": "string", "description": "Custom email message"},
                    "allow_file_discovery": {"type": "boolean", "description": "Allow file discovery"},

                    # Comments
                    "comment_content": {"type": "string", "description": "Comment content"},
                    "anchor": {"type": "string", "description": "Comment anchor for text selection"},

                    # Search parameters
                    "query": {"type": "string", "description": "Custom Drive query string"},
                    "owner": {"type": "string", "description": "File owner filter"},
                    "shared": {"type": "boolean", "description": "Filter shared files"},
                    "trashed": {"type": "boolean", "description": "Include/exclude trashed files"},
                    "modified_after": {"type": "string", "description": "Modified after date (ISO format)"},
                    "modified_before": {"type": "string", "description": "Modified before date (ISO format)"},

                    # Pagination and sorting
                    "page_size": {"type": "integer", "description": "Number of results per page", "default": 100, "maximum": 1000},
                    "page_token": {"type": "string", "description": "Pagination token"},
                    "order_by": {"type": "string", "description": "Sort order (e.g., 'modifiedTime desc', 'name')", "default": "modifiedTime desc"},

                    # Revisions
                    "revision_id": {"type": "string", "description": "Revision ID"},

                    # Metadata fields
                    "fields": {"type": "string", "description": "Specific fields to return"}
                },
                "required": ["action"],
                "additionalProperties": False
            }
        )

    async def cleanup(self):
        """Clean up resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
        self.logger.info("Google Drive tool cleaned up")
