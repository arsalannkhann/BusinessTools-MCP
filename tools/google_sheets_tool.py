"""
Google Sheets integration tool for spreadsheet management and data operations
Provides comprehensive spreadsheet creation, editing, and analysis capabilities
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
import asyncio
from concurrent.futures import ThreadPoolExecutor
import re

import mcp.types as types
from googleapiclient.errors import HttpError

from .base import SalesTool, ToolResult

logger = logging.getLogger(__name__)

def validate_required_params(params: Dict[str, Any], required: List[str]) -> Optional[str]:
    """Validate required parameters"""
    missing = [param for param in required if param not in params or params[param] is None]
    if missing:
        return f"Missing required parameters: {', '.join(missing)}"
    return None

def parse_range(range_str: str) -> Dict[str, Any]:
    """Parse A1 notation range into components"""
    if '!' in range_str:
        sheet_name, cell_range = range_str.split('!', 1)
        sheet_name = sheet_name.strip("'")
    else:
        sheet_name = None
        cell_range = range_str
    
    return {
        'sheet_name': sheet_name,
        'range': cell_range,
        'full_range': range_str
    }

def format_cell_range(sheet_name: str, start_row: int, start_col: int, end_row: int = None, end_col: int = None) -> str:
    """Format cell range in A1 notation"""
    def col_num_to_letter(col_num):
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(ord('A') + col_num % 26) + result
            col_num //= 26
        return result
    
    start_cell = f"{col_num_to_letter(start_col)}{start_row}"
    
    if end_row and end_col:
        end_cell = f"{col_num_to_letter(end_col)}{end_row}"
        range_str = f"{start_cell}:{end_cell}"
    else:
        range_str = start_cell
    
    if sheet_name:
        return f"'{sheet_name}'!{range_str}"
    return range_str

class GoogleSheetsTool(SalesTool):
    """Google Sheets spreadsheet management and data operations tool"""
    
    def __init__(self):
        super().__init__("google_sheets", "Google Sheets spreadsheet management and data operations")
        self.sheets_service = None
        self.google_auth = None
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Google Sheets tool"""
        if not google_auth or not google_auth.is_authenticated():
            self.logger.warning("Google authentication not available")
            return False
        
        try:
            self.google_auth = google_auth
            self.sheets_service = google_auth.get_service('sheets')
            self.logger.info("Google Sheets tool initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Sheets tool: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return self.sheets_service is not None
    
    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition for Google Sheets"""
        return types.Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform",
                        "enum": [
                            "create_spreadsheet", "get_spreadsheet", "update_spreadsheet_properties",
                            "add_sheet", "delete_sheet", "rename_sheet", "duplicate_sheet", "copy_sheet",
                            "read_range", "write_range", "append_data", "clear_range",
                            "insert_rows", "insert_columns", "delete_rows", "delete_columns",
                            "format_cells", "set_column_width", "set_row_height", "merge_cells", "unmerge_cells",
                            "create_chart", "update_chart", "delete_chart",
                            "create_pivot_table", "update_pivot_table", "delete_pivot_table",
                            "sort_range", "filter_data", "find_replace",
                            "protect_sheet", "unprotect_sheet", "share_spreadsheet",
                            "batch_update", "batch_get"
                        ]
                    },
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The ID of the spreadsheet"
                    },
                    "title": {
                        "type": "string", 
                        "description": "Title for spreadsheet or sheet"
                    },
                    "range": {
                        "type": "string",
                        "description": "Cell range in A1 notation (e.g., 'Sheet1!A1:B2')"
                    },
                    "values": {
                        "type": "array",
                        "description": "2D array of values to write",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "required": ["action"]
            }
        )
    
    async def execute(self, action: str, params: Dict[str, Any]) -> ToolResult:
        """Execute Google Sheets action"""
        if not self.sheets_service:
            return self._create_error_result("Google Sheets tool not initialized")
        
        try:
            # Refresh auth if needed
            await self.google_auth.refresh_if_needed()
            
            # Spreadsheet Operations
            if action == "create_spreadsheet":
                return await self._create_spreadsheet(params)
            elif action == "get_spreadsheet":
                return await self._get_spreadsheet(params)
            elif action == "update_spreadsheet_properties":
                return await self._update_spreadsheet_properties(params)
            elif action == "delete_spreadsheet":
                return await self._delete_spreadsheet(params)
            
            # Sheet Management
            elif action == "add_sheet":
                return await self._add_sheet(params)
            elif action == "delete_sheet":
                return await self._delete_sheet(params)
            elif action == "rename_sheet":
                return await self._rename_sheet(params)
            elif action == "duplicate_sheet":
                return await self._duplicate_sheet(params)
            elif action == "copy_sheet":
                return await self._copy_sheet(params)
            
            # Data Operations
            elif action == "read_range":
                return await self._read_range(params)
            elif action == "write_range":
                return await self._write_range(params)
            elif action == "append_data":
                return await self._append_data(params)
            elif action == "clear_range":
                return await self._clear_range(params)
            elif action == "insert_rows":
                return await self._insert_rows(params)
            elif action == "insert_columns":
                return await self._insert_columns(params)
            elif action == "delete_rows":
                return await self._delete_rows(params)
            elif action == "delete_columns":
                return await self._delete_columns(params)
            
            # Formatting and Styling
            elif action == "format_cells":
                return await self._format_cells(params)
            elif action == "set_column_width":
                return await self._set_column_width(params)
            elif action == "set_row_height":
                return await self._set_row_height(params)
            elif action == "merge_cells":
                return await self._merge_cells(params)
            elif action == "unmerge_cells":
                return await self._unmerge_cells(params)
            elif action == "freeze_rows":
                return await self._freeze_rows(params)
            elif action == "freeze_columns":
                return await self._freeze_columns(params)
            
            # Formulas and Functions
            elif action == "set_formula":
                return await self._set_formula(params)
            elif action == "batch_formulas":
                return await self._batch_formulas(params)
            
            # Data Analysis
            elif action == "sort_range":
                return await self._sort_range(params)
            elif action == "filter_data":
                return await self._filter_data(params)
            elif action == "create_pivot_table":
                return await self._create_pivot_table(params)
            elif action == "find_replace":
                return await self._find_replace(params)
            
            # Charts and Visualization
            elif action == "create_chart":
                return await self._create_chart(params)
            elif action == "update_chart":
                return await self._update_chart(params)
            elif action == "delete_chart":
                return await self._delete_chart(params)
            
            # Protection and Permissions
            elif action == "protect_range":
                return await self._protect_range(params)
            elif action == "unprotect_range":
                return await self._unprotect_range(params)
            
            # Batch Operations
            elif action == "batch_update":
                return await self._batch_update(params)
            elif action == "batch_get":
                return await self._batch_get(params)
            
            # Import/Export
            elif action == "import_csv":
                return await self._import_csv(params)
            elif action == "export_csv":
                return await self._export_csv(params)
            
            else:
                return self._create_error_result(f"Unknown action: {action}")
        
        except Exception as e:
            self.logger.error(f"Error executing Google Sheets action {action}: {e}")
            return self._create_error_result(f"Action failed: {str(e)}")
    
    async def _create_spreadsheet(self, params: Dict[str, Any]) -> ToolResult:
        """Create new spreadsheet"""
        try:
            spreadsheet_body = {
                'properties': {
                    'title': params.get('title', 'New Spreadsheet')
                }
            }
            
            # Add initial sheets if specified
            if params.get('sheets'):
                spreadsheet_body['sheets'] = []
                for sheet_config in params['sheets']:
                    sheet = {
                        'properties': {
                            'title': sheet_config.get('title', 'Sheet1'),
                            'gridProperties': {
                                'rowCount': sheet_config.get('row_count', 1000),
                                'columnCount': sheet_config.get('column_count', 26)
                            }
                        }
                    }
                    spreadsheet_body['sheets'].append(sheet)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().create(
                    body=spreadsheet_body
                ).execute()
            )
            
            return self._create_success_result({
                'spreadsheet': result,
                'spreadsheet_id': result['spreadsheetId'],
                'url': result['spreadsheetUrl'],
                'created': True
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to create spreadsheet: {e}")
    
    async def _get_spreadsheet(self, params: Dict[str, Any]) -> ToolResult:
        """Get spreadsheet metadata"""
        error = validate_required_params(params, ["spreadsheet_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            include_grid_data = params.get('include_grid_data', False)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().get(
                    spreadsheetId=spreadsheet_id,
                    includeGridData=include_grid_data
                ).execute()
            )
            
            return self._create_success_result({
                'spreadsheet': result,
                'title': result['properties']['title'],
                'sheets': [sheet['properties']['title'] for sheet in result.get('sheets', [])],
                'sheet_count': len(result.get('sheets', []))
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to get spreadsheet: {e}")
    
    async def _add_sheet(self, params: Dict[str, Any]) -> ToolResult:
        """Add new sheet to spreadsheet"""
        error = validate_required_params(params, ["spreadsheet_id", "title"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': params["title"],
                            'gridProperties': {
                                'rowCount': params.get('row_count', 1000),
                                'columnCount': params.get('column_count', 26)
                            }
                        }
                    }
                }]
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
            )
            
            new_sheet = result['replies'][0]['addSheet']
            
            return self._create_success_result({
                'sheet': new_sheet,
                'sheet_id': new_sheet['properties']['sheetId'],
                'title': new_sheet['properties']['title'],
                'added': True
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to add sheet: {e}")
    
    async def _delete_sheet(self, params: Dict[str, Any]) -> ToolResult:
        """Delete sheet from spreadsheet"""
        error = validate_required_params(params, ["spreadsheet_id", "sheet_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            sheet_id = params["sheet_id"]
            
            request_body = {
                'requests': [{
                    'deleteSheet': {
                        'sheetId': sheet_id
                    }
                }]
            }
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
            )
            
            return self._create_success_result({
                'deleted': True,
                'sheet_id': sheet_id
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to delete sheet: {e}")
    
    async def _read_range(self, params: Dict[str, Any]) -> ToolResult:
        """Read data from spreadsheet range"""
        error = validate_required_params(params, ["spreadsheet_id", "range"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            range_str = params["range"]
            value_render_option = params.get('value_render_option', 'FORMATTED_VALUE')
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_str,
                    valueRenderOption=value_render_option
                ).execute()
            )
            
            values = result.get('values', [])
            
            return self._create_success_result({
                'values': values,
                'range': result.get('range'),
                'major_dimension': result.get('majorDimension'),
                'row_count': len(values),
                'column_count': len(values[0]) if values else 0
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to read range: {e}")
    
    async def _write_range(self, params: Dict[str, Any]) -> ToolResult:
        """Write data to spreadsheet range"""
        error = validate_required_params(params, ["spreadsheet_id", "range", "values"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            range_str = params["range"]
            values = params["values"]
            
            value_input_option = params.get('value_input_option', 'RAW')
            
            body = {
                'values': values,
                'majorDimension': params.get('major_dimension', 'ROWS')
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_str,
                    valueInputOption=value_input_option,
                    body=body
                ).execute()
            )
            
            return self._create_success_result({
                'updated_range': result.get('updatedRange'),
                'updated_rows': result.get('updatedRows'),
                'updated_columns': result.get('updatedColumns'),
                'updated_cells': result.get('updatedCells'),
                'written': True
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to write range: {e}")
    
    async def _append_data(self, params: Dict[str, Any]) -> ToolResult:
        """Append data to spreadsheet"""
        error = validate_required_params(params, ["spreadsheet_id", "range", "values"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            range_str = params["range"]
            values = params["values"]
            
            value_input_option = params.get('value_input_option', 'RAW')
            insert_data_option = params.get('insert_data_option', 'INSERT_ROWS')
            
            body = {
                'values': values,
                'majorDimension': params.get('major_dimension', 'ROWS')
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id,
                    range=range_str,
                    valueInputOption=value_input_option,
                    insertDataOption=insert_data_option,
                    body=body
                ).execute()
            )
            
            return self._create_success_result({
                'spreadsheet_id': result.get('spreadsheetId'),
                'table_range': result.get('tableRange'),
                'updates': result.get('updates', {}),
                'appended': True
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to append data: {e}")
    
    async def _clear_range(self, params: Dict[str, Any]) -> ToolResult:
        """Clear data from spreadsheet range"""
        error = validate_required_params(params, ["spreadsheet_id", "range"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            range_str = params["range"]
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=range_str
                ).execute()
            )
            
            return self._create_success_result({
                'cleared_range': result.get('clearedRange'),
                'cleared': True
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to clear range: {e}")
    
    async def _format_cells(self, params: Dict[str, Any]) -> ToolResult:
        """Format cells in spreadsheet"""
        error = validate_required_params(params, ["spreadsheet_id", "range"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            range_info = parse_range(params["range"])
            
            # Build format request
            format_request = {
                'repeatCell': {
                    'range': self._parse_range_to_grid_range(params["range"]),
                    'cell': {
                        'userEnteredFormat': {}
                    },
                    'fields': 'userEnteredFormat'
                }
            }
            
            # Add formatting options
            user_format = format_request['repeatCell']['cell']['userEnteredFormat']
            
            if params.get('background_color'):
                user_format['backgroundColor'] = self._parse_color(params['background_color'])
            
            if params.get('text_color'):
                user_format['textFormat'] = {'foregroundColor': self._parse_color(params['text_color'])}
            
            if params.get('bold'):
                if 'textFormat' not in user_format:
                    user_format['textFormat'] = {}
                user_format['textFormat']['bold'] = params['bold']
            
            if params.get('italic'):
                if 'textFormat' not in user_format:
                    user_format['textFormat'] = {}
                user_format['textFormat']['italic'] = params['italic']
            
            if params.get('font_size'):
                if 'textFormat' not in user_format:
                    user_format['textFormat'] = {}
                user_format['textFormat']['fontSize'] = params['font_size']
            
            if params.get('number_format'):
                user_format['numberFormat'] = {
                    'type': params['number_format'],
                    'pattern': params.get('number_pattern', '')
                }
            
            if params.get('horizontal_alignment'):
                user_format['horizontalAlignment'] = params['horizontal_alignment']
            
            if params.get('vertical_alignment'):
                user_format['verticalAlignment'] = params['vertical_alignment']
            
            request_body = {
                'requests': [format_request]
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
            )
            
            return self._create_success_result({
                'formatted': True,
                'range': params["range"],
                'spreadsheet_id': result.get('spreadsheetId')
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to format cells: {e}")
    
    async def _set_formula(self, params: Dict[str, Any]) -> ToolResult:
        """Set formula in cell"""
        error = validate_required_params(params, ["spreadsheet_id", "range", "formula"])
        if error:
            return self._create_error_result(error)
        
        try:
            formula = params["formula"]
            if not formula.startswith('='):
                formula = '=' + formula
            
            # Use write_range with formula
            write_params = {
                "spreadsheet_id": params["spreadsheet_id"],
                "range": params["range"],
                "values": [[formula]],
                "value_input_option": "USER_ENTERED"  # This processes formulas
            }
            
            return await self._write_range(write_params)
            
        except Exception as e:
            return self._create_error_result(f"Failed to set formula: {e}")
    
    async def _sort_range(self, params: Dict[str, Any]) -> ToolResult:
        """Sort data in range"""
        error = validate_required_params(params, ["spreadsheet_id", "range"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            
            # Build sort request
            sort_request = {
                'sortRange': {
                    'range': self._parse_range_to_grid_range(params["range"]),
                    'sortSpecs': []
                }
            }
            
            # Add sort specifications
            sort_columns = params.get('sort_columns', [{'column': 0, 'ascending': True}])
            
            for sort_spec in sort_columns:
                sort_request['sortRange']['sortSpecs'].append({
                    'dimensionIndex': sort_spec.get('column', 0),
                    'sortOrder': 'ASCENDING' if sort_spec.get('ascending', True) else 'DESCENDING'
                })
            
            request_body = {
                'requests': [sort_request]
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
            )
            
            return self._create_success_result({
                'sorted': True,
                'range': params["range"],
                'sort_specs': sort_columns
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to sort range: {e}")
    
    async def _create_chart(self, params: Dict[str, Any]) -> ToolResult:
        """Create chart in spreadsheet"""
        error = validate_required_params(params, ["spreadsheet_id", "sheet_id", "chart_type"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            sheet_id = params["sheet_id"]
            
            # Build chart request
            chart_request = {
                'addChart': {
                    'chart': {
                        'spec': {
                            'title': params.get('title', 'Chart'),
                            'basicChart': {
                                'chartType': params["chart_type"].upper(),
                                'legendPosition': params.get('legend_position', 'BOTTOM_LEGEND'),
                                'axis': [
                                    {
                                        'position': 'BOTTOM_AXIS',
                                        'title': params.get('x_axis_title', '')
                                    },
                                    {
                                        'position': 'LEFT_AXIS', 
                                        'title': params.get('y_axis_title', '')
                                    }
                                ],
                                'domains': [],
                                'series': []
                            }
                        },
                        'position': {
                            'overlayPosition': {
                                'anchorCell': {
                                    'sheetId': sheet_id,
                                    'rowIndex': params.get('position_row', 0),
                                    'columnIndex': params.get('position_column', 0)
                                }
                            }
                        }
                    }
                }
            }
            
            # Add data ranges if provided
            if params.get('data_range'):
                chart_request['addChart']['chart']['spec']['basicChart']['domains'].append({
                    'domain': self._parse_range_to_grid_range(params['data_range'])
                })
            
            if params.get('series_ranges'):
                for series_range in params['series_ranges']:
                    chart_request['addChart']['chart']['spec']['basicChart']['series'].append({
                        'series': self._parse_range_to_grid_range(series_range),
                        'targetAxis': 'LEFT_AXIS'
                    })
            
            request_body = {
                'requests': [chart_request]
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
            )
            
            chart = result['replies'][0]['addChart']['chart']
            
            return self._create_success_result({
                'chart': chart,
                'chart_id': chart['chartId'],
                'created': True
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to create chart: {e}")
    
    async def _batch_update(self, params: Dict[str, Any]) -> ToolResult:
        """Execute multiple update requests in batch"""
        error = validate_required_params(params, ["spreadsheet_id", "requests"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            requests = params["requests"]
            
            request_body = {
                'requests': requests,
                'includeSpreadsheetInResponse': params.get('include_response', False)
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request_body
                ).execute()
            )
            
            return self._create_success_result({
                'replies': result.get('replies', []),
                'updated_spreadsheet': result.get('updatedSpreadsheet'),
                'batch_executed': True,
                'request_count': len(requests)
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to execute batch update: {e}")
    
    async def _batch_get(self, params: Dict[str, Any]) -> ToolResult:
        """Get multiple ranges in batch"""
        error = validate_required_params(params, ["spreadsheet_id", "ranges"])
        if error:
            return self._create_error_result(error)
        
        try:
            spreadsheet_id = params["spreadsheet_id"]
            ranges = params["ranges"]
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sheets_service.spreadsheets().values().batchGet(
                    spreadsheetId=spreadsheet_id,
                    ranges=ranges,
                    valueRenderOption=params.get('value_render_option', 'FORMATTED_VALUE')
                ).execute()
            )
            
            return self._create_success_result({
                'value_ranges': result.get('valueRanges', []),
                'spreadsheet_id': result.get('spreadsheetId'),
                'range_count': len(result.get('valueRanges', []))
            })
            
        except HttpError as e:
            return self._create_error_result(f"Failed to batch get ranges: {e}")
    
    def _parse_color(self, color: Union[str, Dict]) -> Dict[str, float]:
        """Parse color to Google Sheets color format"""
        if isinstance(color, dict):
            return color
        
        # Handle hex colors
        if isinstance(color, str) and color.startswith('#'):
            hex_color = color[1:]
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                return {'red': r, 'green': g, 'blue': b}
        
        # Handle named colors
        colors = {
            'red': {'red': 1.0, 'green': 0.0, 'blue': 0.0},
            'green': {'red': 0.0, 'green': 1.0, 'blue': 0.0},
            'blue': {'red': 0.0, 'green': 0.0, 'blue': 1.0},
            'white': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
            'black': {'red': 0.0, 'green': 0.0, 'blue': 0.0},
            'yellow': {'red': 1.0, 'green': 1.0, 'blue': 0.0}
        }
        
        return colors.get(color.lower(), {'red': 0.0, 'green': 0.0, 'blue': 0.0})
    