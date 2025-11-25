# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
from typing import List, Optional

# Official Brave Search implementation using brave-search package
import json
from typing import Dict, Any

# Official Brave Search implementation using brave-search package
import json
from typing import Dict, Any, Optional
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
    
    def __init__(self, api_key: str = None, name: str = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if name:
            self.name = name
        try:
            from brave_search import BraveSearch as BraveSearchAPI
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
    
    def __init__(self, name: str = None, num_results: int = 5, **kwargs):
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

from src.config import SELECTED_SEARCH_ENGINE, SearchEngine, load_yaml_config
from src.tools.decorators import create_logged_tool
from src.tools.tavily_search.tavily_search_results_with_images import (
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


# Get the selected search tool
def get_web_search_tool(max_search_results: int):
    search_config = get_search_config()

    if SELECTED_SEARCH_ENGINE == SearchEngine.TAVILY.value:
        # Get all Tavily search parameters from configuration with defaults
        include_domains: Optional[List[str]] = search_config.get("include_domains", [])
        exclude_domains: Optional[List[str]] = search_config.get("exclude_domains", [])
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

        return LoggedTavilySearch(
            name="web_search",
            max_results=max_search_results,
            include_answer=include_answer,
            search_depth=search_depth,
            include_raw_content=include_raw_content,
            include_images=include_images,
            include_image_descriptions=include_image_descriptions,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
    elif SELECTED_SEARCH_ENGINE == SearchEngine.DUCKDUCKGO.value:
        return LoggedDuckDuckGoSearch(
            name="web_search",
            num_results=max_search_results,
        )
    elif SELECTED_SEARCH_ENGINE == SearchEngine.BRAVE_SEARCH.value:
        return LoggedBraveSearch(
            name="web_search",
            search_wrapper=BraveSearchWrapper(
                api_key=os.getenv("BRAVE_SEARCH_API_KEY", ""),
                search_kwargs={"count": max_search_results},
            ),
        )
    elif SELECTED_SEARCH_ENGINE == SearchEngine.ARXIV.value:
        return LoggedArxivSearch(
            name="web_search",
            api_wrapper=ArxivAPIWrapper(
                top_k_results=max_search_results,
                load_max_docs=max_search_results,
                load_all_available_meta=True,
            ),
        )
    elif SELECTED_SEARCH_ENGINE == SearchEngine.SEARX.value:
        return LoggedSearxSearch(
            name="web_search",
            wrapper=SearxSearchWrapper(
                k=max_search_results,
            ),
        )
    elif SELECTED_SEARCH_ENGINE == SearchEngine.WIKIPEDIA.value:
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
        raise ValueError(f"Unsupported search engine: {SELECTED_SEARCH_ENGINE}")
