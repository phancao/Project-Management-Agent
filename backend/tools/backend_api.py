# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
from typing import Annotated

import requests
from langchain_core.tools import tool

from .decorators import log_io

logger = logging.getLogger(__name__)


@tool
@log_io
def backend_api_call(
    endpoint: Annotated[str, "The API endpoint path (e.g., '/api/pm/providers?include_credentials=true')"],
    method: Annotated[str, "HTTP method: 'GET', 'POST', 'PUT', 'DELETE'"] = "GET",
    base_url: Annotated[str, "Base URL of the backend API"] = "http://localhost:8000",
) -> str:
    """
    Call the backend API endpoint and return the response.
    
    Use this tool to retrieve data from the backend API, such as:
    - Getting PM provider configurations: '/api/pm/providers?include_credentials=true'
    - Other backend API endpoints as needed
    
    Args:
        endpoint: The API endpoint path (e.g., '/api/pm/providers?include_credentials=true')
        method: HTTP method (default: 'GET')
        base_url: Base URL of the backend API (default: 'http://localhost:8000')
    
    Returns:
        JSON string containing the API response
    """
    try:
        url = f"{base_url}{endpoint}"
        logger.info(f"Calling backend API: {method} {url}")
        
        response = requests.request(
            method=method,
            url=url,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        
        if response.status_code != 200:
            error_msg = f"API returned status {response.status_code}: {response.text}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg, "status_code": response.status_code})
        
        try:
            data = response.json()
            return json.dumps(data)
        except json.JSONDecodeError:
            # If response is not JSON, return as text
            return json.dumps({"content": response.text})
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to call backend API: {repr(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Unexpected error calling backend API: {repr(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"error": error_msg})

