"""
Google Search integration tool
Handles web search operations using Google Custom Search API
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
import mcp.types as types
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
from .base import SalesTool, ToolResult, validate_required_params


class GoogleSearchTool(SalesTool):
    """Google Search operations using Custom Search API"""
    
    def __init__(self):
        super().__init__("google_search", "Google Search integration for web search operations")
        self.api_key = None
        self.cse_id = None
        self.service = None
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Google Search API connection"""
        try:
            # Get API key and Custom Search Engine ID from settings
            self.api_key = getattr(settings, 'google_search_api_key', None)
            self.cse_id = getattr(settings, 'google_search_cse_id', None)
            
            if not self.api_key:
                self.logger.warning("Google Search API key not configured")
                return False
                
            if not self.cse_id:
                self.logger.warning("Google Custom Search Engine ID not configured")
                return False
            
            # Initialize the Custom Search API service
            loop = asyncio.get_event_loop()
            self.service = await loop.run_in_executor(
                self.executor,
                lambda: build("customsearch", "v1", developerKey=self.api_key)
            )
            
            # Test the connection with a simple search
            await self._test_search_connection()
            
            self.logger.info("Google Search API connection validated")
            return True
            
        except Exception as e:
            self.logger.error(f"Google Search API initialization failed: {e}")
            return False
    
    async def _test_search_connection(self):
        """Test Google Search API connection"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self.service.cse().list(q="test", cx=self.cse_id, num=1).execute()
            )
        except Exception as e:
            raise Exception(f"Search API test failed: {e}")
    
    def is_configured(self) -> bool:
        """Check if tool is properly configured"""
        return bool(self.api_key and self.cse_id and self.service)
    
    async def execute(self, action: str, params: Dict[str, Any]) -> ToolResult:
        """Execute Google Search operations"""
        try:
            if action == "search":
                return await self._search(params)
            elif action == "search_images":
                return await self._search_images(params)
            elif action == "search_news":
                return await self._search_news(params)
            elif action == "search_site":
                return await self._search_site(params)
            elif action == "search_filetype":
                return await self._search_filetype(params)
            else:
                return self._create_error_result(f"Unknown action: {action}")
        
        except Exception as e:
            return self._create_error_result(f"Google Search operation failed: {str(e)}")
    
    async def _search(self, params: Dict[str, Any]) -> ToolResult:
        """Perform web search"""
        # Validate required parameters
        validation_error = validate_required_params(params, ['query'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        query = params['query']
        num_results = params.get('num_results', 10)  # Default to 10 results
        start_index = params.get('start_index', 1)   # Default to start from 1
        safe_search = params.get('safe_search', 'medium')  # off, medium, high
        language = params.get('language', 'en')
        country = params.get('country', 'us')
        
        # Limit results to maximum of 10 per request (API limitation)
        num_results = min(num_results, 10)
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.service.cse().list(
                    q=query,
                    cx=self.cse_id,
                    num=num_results,
                    start=start_index,
                    safe=safe_search,
                    lr=f"lang_{language}",
                    gl=country
                ).execute()
            )
            
            # Parse and format results
            search_results = self._format_search_results(result)
            
            return self._create_success_result(
                data=search_results,
                metadata={
                    'query': query,
                    'total_results': result.get('searchInformation', {}).get('totalResults', '0'),
                    'search_time': result.get('searchInformation', {}).get('searchTime', '0')
                }
            )
            
        except HttpError as e:
            return self._create_error_result(f"Google Search API error: {e}")
        except Exception as e:
            return self._create_error_result(f"Search failed: {e}")
    
    async def _search_images(self, params: Dict[str, Any]) -> ToolResult:
        """Search for images"""
        validation_error = validate_required_params(params, ['query'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        query = params['query']
        num_results = min(params.get('num_results', 10), 10)
        image_size = params.get('image_size', 'MEDIUM')  # ICON, SMALL, MEDIUM, LARGE, XLARGE, XXLARGE, HUGE
        image_type = params.get('image_type', 'photo')   # clipart, face, lineart, stock, photo, animated
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.service.cse().list(
                    q=query,
                    cx=self.cse_id,
                    num=num_results,
                    searchType='image',
                    imgSize=image_size,
                    imgType=image_type
                ).execute()
            )
            
            # Parse and format image results
            image_results = self._format_image_results(result)
            
            return self._create_success_result(
                data=image_results,
                metadata={
                    'query': query,
                    'search_type': 'images',
                    'total_results': result.get('searchInformation', {}).get('totalResults', '0')
                }
            )
            
        except HttpError as e:
            return self._create_error_result(f"Google Image Search API error: {e}")
        except Exception as e:
            return self._create_error_result(f"Image search failed: {e}")
    
    async def _search_news(self, params: Dict[str, Any]) -> ToolResult:
        """Search for news articles"""
        validation_error = validate_required_params(params, ['query'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        query = params['query']
        num_results = min(params.get('num_results', 10), 10)
        sort_by = params.get('sort_by', 'date')  # date or relevance
        time_period = params.get('time_period', '')  # d1 (past day), w1 (past week), m1 (past month), y1 (past year)
        
        # Add news-specific search operators
        search_query = f"{query} news"
        if time_period:
            search_query += f" dateRestrict:{time_period}"
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.service.cse().list(
                    q=search_query,
                    cx=self.cse_id,
                    num=num_results,
                    sort=sort_by if sort_by == 'date' else None
                ).execute()
            )
            
            # Parse and format news results
            news_results = self._format_search_results(result)
            
            return self._create_success_result(
                data=news_results,
                metadata={
                    'query': query,
                    'search_type': 'news',
                    'sort_by': sort_by,
                    'time_period': time_period,
                    'total_results': result.get('searchInformation', {}).get('totalResults', '0')
                }
            )
            
        except HttpError as e:
            return self._create_error_result(f"Google News Search API error: {e}")
        except Exception as e:
            return self._create_error_result(f"News search failed: {e}")
    
    async def _search_site(self, params: Dict[str, Any]) -> ToolResult:
        """Search within a specific website"""
        validation_error = validate_required_params(params, ['query', 'site'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        query = params['query']
        site = params['site']
        num_results = min(params.get('num_results', 10), 10)
        
        # Add site-specific search operator
        search_query = f"site:{site} {query}"
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.service.cse().list(
                    q=search_query,
                    cx=self.cse_id,
                    num=num_results
                ).execute()
            )
            
            # Parse and format results
            site_results = self._format_search_results(result)
            
            return self._create_success_result(
                data=site_results,
                metadata={
                    'query': query,
                    'site': site,
                    'search_type': 'site_specific',
                    'total_results': result.get('searchInformation', {}).get('totalResults', '0')
                }
            )
            
        except HttpError as e:
            return self._create_error_result(f"Google Site Search API error: {e}")
        except Exception as e:
            return self._create_error_result(f"Site search failed: {e}")
    
    async def _search_filetype(self, params: Dict[str, Any]) -> ToolResult:
        """Search for specific file types"""
        validation_error = validate_required_params(params, ['query', 'filetype'])
        if validation_error:
            return self._create_error_result(validation_error)
        
        query = params['query']
        filetype = params['filetype'].lower()  # pdf, doc, ppt, xls, etc.
        num_results = min(params.get('num_results', 10), 10)
        
        # Add filetype search operator
        search_query = f"filetype:{filetype} {query}"
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.service.cse().list(
                    q=search_query,
                    cx=self.cse_id,
                    num=num_results
                ).execute()
            )
            
            # Parse and format results
            filetype_results = self._format_search_results(result)
            
            return self._create_success_result(
                data=filetype_results,
                metadata={
                    'query': query,
                    'filetype': filetype,
                    'search_type': 'filetype_specific',
                    'total_results': result.get('searchInformation', {}).get('totalResults', '0')
                }
            )
            
        except HttpError as e:
            return self._create_error_result(f"Google Filetype Search API error: {e}")
        except Exception as e:
            return self._create_error_result(f"Filetype search failed: {e}")
    
    def _format_search_results(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format search results into a consistent structure"""
        formatted_results = []
        
        items = result.get('items', [])
        for item in items:
            formatted_item = {
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'display_link': item.get('displayLink', ''),
                'formatted_url': item.get('formattedUrl', '')
            }
            
            # Add page map data if available
            if 'pagemap' in item:
                pagemap = item['pagemap']
                if 'metatags' in pagemap and pagemap['metatags']:
                    metatag = pagemap['metatags'][0]
                    formatted_item['meta_description'] = metatag.get('og:description', metatag.get('description', ''))
                    formatted_item['meta_image'] = metatag.get('og:image', '')
            
            formatted_results.append(formatted_item)
        
        return formatted_results
    
    def _format_image_results(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format image search results"""
        formatted_results = []
        
        items = result.get('items', [])
        for item in items:
            image_info = item.get('image', {})
            formatted_item = {
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'image_url': image_info.get('thumbnailLink', ''),
                'context_link': image_info.get('contextLink', ''),
                'width': image_info.get('width', 0),
                'height': image_info.get('height', 0),
                'thumbnail_width': image_info.get('thumbnailWidth', 0),
                'thumbnail_height': image_info.get('thumbnailHeight', 0),
                'snippet': item.get('snippet', ''),
                'display_link': item.get('displayLink', '')
            }
            
            formatted_results.append(formatted_item)
        
        return formatted_results
    
    def get_mcp_tool_definition(self) -> types.Tool:
        """Return MCP tool definition for Google Search"""
        return types.Tool(
            name="google_search",
            description="Search the web using Google Custom Search API with various search types and filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "search_images", "search_news", "search_site", "search_filetype"],
                        "description": "The search action to perform"
                    },
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 10,
                        "description": "Number of results to return (max 10)"
                    },
                    "start_index": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 1,
                        "description": "Starting index for results (pagination)"
                    },
                    "safe_search": {
                        "type": "string",
                        "enum": ["off", "medium", "high"],
                        "default": "medium",
                        "description": "Safe search setting"
                    },
                    "language": {
                        "type": "string",
                        "default": "en",
                        "description": "Language for search results (e.g., 'en', 'es', 'fr')"
                    },
                    "country": {
                        "type": "string",
                        "default": "us",
                        "description": "Country for search results (e.g., 'us', 'uk', 'ca')"
                    },
                    "site": {
                        "type": "string",
                        "description": "Specific website to search within (for search_site action)"
                    },
                    "filetype": {
                        "type": "string",
                        "description": "File type to search for (for search_filetype action, e.g., 'pdf', 'doc')"
                    },
                    "image_size": {
                        "type": "string",
                        "enum": ["ICON", "SMALL", "MEDIUM", "LARGE", "XLARGE", "XXLARGE", "HUGE"],
                        "default": "MEDIUM",
                        "description": "Image size filter (for search_images action)"
                    },
                    "image_type": {
                        "type": "string",
                        "enum": ["clipart", "face", "lineart", "stock", "photo", "animated"],
                        "default": "photo",
                        "description": "Image type filter (for search_images action)"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["relevance", "date"],
                        "default": "relevance",
                        "description": "Sort order for results (for search_news action)"
                    },
                    "time_period": {
                        "type": "string",
                        "enum": ["", "d1", "w1", "m1", "y1"],
                        "default": "",
                        "description": "Time period filter (for search_news: d1=past day, w1=past week, m1=past month, y1=past year)"
                    }
                },
                "required": ["action", "query"]
            }
        )
    
    async def cleanup(self):
        """Clean up resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
