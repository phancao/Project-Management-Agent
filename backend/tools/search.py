# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import json
from typing import List, Optional, Any
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

class BraveSearch(BaseTool):
    """
    Official Brave Search implementation using brave-search package
    """
    name: str = "brave_search"
    description: str = "Search the web using Brave Search. Input should be a search query string."
    
    api_key: Optional[str] = None
    brave_api: Any = None
    
    def __init__(self, api_key: Optional[str] = None, name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if name:
            self.name = name
        try:
            from brave_search import BraveSearch as BraveSearchAPI  # type: ignore[import]
            self.brave_api = BraveSearchAPI(api_key=self.api_key)
        except ImportError:
            self.brave_api = None
    
    def _run(
        self, 
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """
        Execute Brave Search query using official package
        
        Args:
            query: Search query string
            
        Returns:
            JSON string with search results or error message
        """
        if not self.brave_api:
            return f"BraveSearch ERROR: brave-search package not installed. Please install with: pip install brave-search"
        
        if not self.api_key:
            return f"BraveSearch ERROR: No API key provided. Please set BRAVE_API_KEY environment variable or pass api_key parameter."
        
        try:
            results = self.brave_api.search(query, count=5)
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "description": result.get("description", "")
                })
            return json.dumps(formatted_results, indent=2)
        except Exception as e:
            return f"BraveSearch ERROR: {str(e)}"

class DuckDuckGoSearchResults(BaseTool):
    """
    Official DuckDuckGo Search implementation using duckduckgo-search package
    """
    name: str = "duckduckgo_search"
    description: str = "Search the web using DuckDuckGo. Input should be a search query string."
    
    num_results: int = 5
    ddgs: Any = None
    
    def __init__(self, name: Optional[str] = None, num_results: int = 5, **kwargs):
        super().__init__(**kwargs)
        if name:
            self.name = name
        self.num_results = num_results
        try:
            from duckduckgo_search import DDGS
            self.ddgs = DDGS()
        except ImportError:
            self.ddgs = None
    
    def _run(
        self, 
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """
        Execute DuckDuckGo search query
        
        Args:
            query: Search query string
            
        Returns:
            JSON string with search results or error message
        """
        if not self.ddgs:
            return f"DuckDuckGo ERROR: duckduckgo-search package not installed. Please install with: pip install duckduckgo-search"
        
        try:
            results = []
            for result in self.ddgs.text(query, max_results=self.num_results):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "description": result.get("body", "")
                })
            return json.dumps(results, indent=2)
        except Exception as e:
            return f"DuckDuckGo ERROR: {str(e)}"

class SearxSearchRun:
    def __init__(self, **kwargs):
        pass
    
    def run(self, query: str) -> str:
        return f"Searx mock results for: {query}"

class WikipediaQueryRun:
    def __init__(self, **kwargs):
        pass
    
    def run(self, query: str) -> str:
        return f"Wikipedia mock results for: {query}"

class ArxivQueryRun:
    def __init__(self, **kwargs):
        pass
    
    def run(self, query: str) -> str:
        return f"Arxiv mock results for: {query}"

# Mock wrappers
class BraveSearchWrapper:
    def __init__(self, **kwargs):
        pass

class SearxSearchWrapper:
    def __init__(self, **kwargs):
        pass

class WikipediaAPIWrapper:
    def __init__(self, **kwargs):
        pass

class ArxivAPIWrapper:
    def __init__(self, **kwargs):
        pass

from shared.config import SELECTED_SEARCH_ENGINE, SearchEngine, load_yaml_config
from backend.tools.decorators import create_logged_tool
from backend.tools.tavily_search.tavily_search_results_with_images import (
    TavilySearchWithImages,
)

logger = logging.getLogger(__name__)

# Create logged versions of the search tools
LoggedTavilySearch = create_logged_tool(TavilySearchWithImages)
LoggedDuckDuckGoSearch = create_logged_tool(DuckDuckGoSearchResults)
LoggedBraveSearch = create_logged_tool(BraveSearch)
LoggedArxivSearch = create_logged_tool(ArxivQueryRun)
LoggedSearxSearch = create_logged_tool(SearxSearchRun)
LoggedWikipediaSearch = create_logged_tool(WikipediaQueryRun)


def get_search_config():
    config = load_yaml_config("conf.yaml")
    search_config = config.get("SEARCH_ENGINE", {})
    return search_config


def get_search_provider_from_db(provider_id: Optional[str] = None):
    """Get search provider configuration from database"""
    try:
        from database.connection import get_db_session
        from database.orm_models import SearchProviderAPIKey
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            if provider_id:
                # Get specific provider
                provider = db.query(SearchProviderAPIKey).filter(
                    SearchProviderAPIKey.provider_id == provider_id,
                    SearchProviderAPIKey.is_active.is_(True)
                ).first()
                # If specific provider not found, fall back to default DuckDuckGo
                if not provider and provider_id == "duckduckgo":
                    logger.info(f"Using default DuckDuckGo provider (no configuration needed)")
                    return {
                        "provider_id": "duckduckgo",
                        "provider_name": "DuckDuckGo",
                        "api_key": None,
                        "base_url": None,
                        "additional_config": {},
                    }
            else:
                # Get default provider
                provider = db.query(SearchProviderAPIKey).filter(
                    SearchProviderAPIKey.is_default.is_(True),
                    SearchProviderAPIKey.is_active.is_(True)
                ).first()
                
                # If no default, get first active provider
                if not provider:
                    provider = db.query(SearchProviderAPIKey).filter(
                        SearchProviderAPIKey.is_active.is_(True)
                    ).first()
            
            if provider:
                return {
                    "provider_id": str(provider.provider_id),
                    "provider_name": str(provider.provider_name),
                    "api_key": str(provider.api_key) if provider.api_key else None,
                    "base_url": str(provider.base_url) if provider.base_url else None,
                    "additional_config": provider.additional_config if provider.additional_config else {},
                }
            # Return default free provider (DuckDuckGo) when no provider is configured
            logger.info("No search provider found in database, using default DuckDuckGo")
            return {
                "provider_id": "duckduckgo",
                "provider_name": "DuckDuckGo",
                "api_key": None,
                "base_url": None,
                "additional_config": {},
            }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to get search provider from database: {e}. Using default DuckDuckGo.")
        # Return default free provider (DuckDuckGo) when database query fails
        return {
            "provider_id": "duckduckgo",
            "provider_name": "DuckDuckGo",
            "api_key": None,
            "base_url": None,
            "additional_config": {},
        }


# Get the selected search tool
def get_web_search_tool(max_search_results: int, provider_id: Optional[str] = None):
    # Try to get provider from database first
    db_provider = get_search_provider_from_db(provider_id)
    
    # Determine which provider to use
    # db_provider will always return a value (defaults to DuckDuckGo if none configured)
    selected_provider = db_provider["provider_id"]
    api_key = db_provider.get("api_key")
    base_url = db_provider.get("base_url")
    additional_config = db_provider.get("additional_config", {})
    logger.info(f"Using search provider: {selected_provider}")
    
    search_config = get_search_config()
    # Merge additional_config from database with search_config from yaml
    if additional_config:
        search_config = {**search_config, **additional_config}

    if selected_provider == SearchEngine.TAVILY.value or selected_provider == "tavily":
        # Get all Tavily search parameters from configuration with defaults
        include_domains_raw = search_config.get("include_domains", [])
        exclude_domains_raw = search_config.get("exclude_domains", [])
        include_domains: List[str] = include_domains_raw if isinstance(include_domains_raw, list) else []
        exclude_domains: List[str] = exclude_domains_raw if isinstance(exclude_domains_raw, list) else []
        include_answer: bool = search_config.get("include_answer", False)
        search_depth: str = search_config.get("search_depth", "advanced")
        include_raw_content: bool = search_config.get("include_raw_content", True)
        include_images: bool = search_config.get("include_images", True)
        include_image_descriptions: bool = include_images and search_config.get(
            "include_image_descriptions", True
        )

        logger.info(
            f"Tavily search configuration loaded: include_domains={include_domains}, "
            f"exclude_domains={exclude_domains}, include_answer={include_answer}, "
            f"search_depth={search_depth}, include_raw_content={include_raw_content}, "
            f"include_images={include_images}, include_image_descriptions={include_image_descriptions}"
        )

        try:
            # Create API wrapper with API key if available from database
            from backend.tools.tavily_search.tavily_search_api_wrapper import EnhancedTavilySearchAPIWrapper
            
            # Initialize API wrapper with API key (required for Tavily)
            if api_key:
                logger.info("Using Tavily API key from database")
                api_wrapper = EnhancedTavilySearchAPIWrapper(tavily_api_key=api_key)
            else:
                # Try to use environment variable as fallback
                import os
                env_api_key = os.getenv("TAVILY_API_KEY")
                if env_api_key:
                    logger.info("Using Tavily API key from environment variable")
                    api_wrapper = EnhancedTavilySearchAPIWrapper(tavily_api_key=env_api_key)
                else:
                    raise ValueError("Tavily API key is required. Please configure it in the database or set TAVILY_API_KEY environment variable.")
            
            # Create Tavily search tool with the API wrapper
            tavily_kwargs = {
                "name": "web_search",
                "max_results": max_search_results,
                "include_answer": include_answer,
                "search_depth": search_depth,
                "include_raw_content": include_raw_content,
                "include_images": include_images,
                "include_image_descriptions": include_image_descriptions,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "api_wrapper": api_wrapper,  # Pass the initialized wrapper
            }
            
            return LoggedTavilySearch(**tavily_kwargs)
        except Exception as e:
            logger.warning(f"Failed to initialize Tavily search: {e}. Falling back to DuckDuckGo.")
            # Fall back to DuckDuckGo
            return LoggedDuckDuckGoSearch(
                name="web_search",
                max_results=max_search_results,
            )
    elif selected_provider == SearchEngine.DUCKDUCKGO.value or selected_provider == "duckduckgo":
        return LoggedDuckDuckGoSearch(
            name="web_search",
            num_results=max_search_results,
        )
    elif selected_provider == SearchEngine.BRAVE_SEARCH.value or selected_provider == "brave_search":
        # Use API key from database if available, otherwise fall back to environment variable
        brave_api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY", "")
        return LoggedBraveSearch(
            name="web_search",
            api_key=brave_api_key,
        )
    elif selected_provider == SearchEngine.ARXIV.value or selected_provider == "arxiv":
        return LoggedArxivSearch(
            name="web_search",
            api_wrapper=ArxivAPIWrapper(
                top_k_results=max_search_results,
                load_max_docs=max_search_results,
                load_all_available_meta=True,
            ),
        )
    elif selected_provider == SearchEngine.SEARX.value or selected_provider == "searx":
        # Use base_url from database if available
        searx_base_url = base_url or os.getenv("SEARX_BASE_URL", "https://searx.be")
        return LoggedSearxSearch(
            name="web_search",
            wrapper=SearxSearchWrapper(
                k=max_search_results,
                base_url=searx_base_url,
            ),
        )
    elif selected_provider == SearchEngine.WIKIPEDIA.value or selected_provider == "wikipedia":
        wiki_lang = search_config.get("wikipedia_lang", "en")
        wiki_doc_content_chars_max = search_config.get(
            "wikipedia_doc_content_chars_max", 4000
        )
        return LoggedWikipediaSearch(
            name="web_search",
            api_wrapper=WikipediaAPIWrapper(
                lang=wiki_lang,
                top_k_results=max_search_results,
                load_all_available_meta=True,
                doc_content_chars_max=wiki_doc_content_chars_max,
            ),
        )
    else:
        raise ValueError(f"Unsupported search engine: {selected_provider}")
