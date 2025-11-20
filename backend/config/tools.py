# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import enum
import os

from dotenv import load_dotenv

load_dotenv()


class SearchEngine(enum.Enum):
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"
    BRAVE_SEARCH = "brave_search"
    ARXIV = "arxiv"
    SEARX = "searx"
    WIKIPEDIA = "wikipedia"


# Tool configuration
SELECTED_SEARCH_ENGINE = os.getenv("SEARCH_API", SearchEngine.TAVILY.value)


class RAGProvider(enum.Enum):
    DIFY = "dify"
    RAGFLOW = "ragflow"
    VIKINGDB_KNOWLEDGE_BASE = "vikingdb_knowledge_base"
    MOI = "moi"
    MILVUS = "milvus"


SELECTED_RAG_PROVIDER = os.getenv("RAG_PROVIDER")


class PMProvider(enum.Enum):
    """Project Management provider types"""
    INTERNAL = "internal"  # Our internal database
    OPENPROJECT = "openproject"
    JIRA = "jira"
    CLICKUP = "clickup"
    ASANA = "asana"
    TRELLO = "trello"


SELECTED_PM_PROVIDER = os.getenv("PM_PROVIDER", PMProvider.INTERNAL.value)
