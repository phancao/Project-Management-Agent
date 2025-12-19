#!/usr/bin/env python3
"""
Script to update markdown documentation files with new directory structure
Replaces old paths (src/, mcp_server, etc.) with new paths (backend/, mcp_server/, etc.)
"""

import os
import re
from pathlib import Path

# Mapping of old patterns to new patterns
REPLACEMENTS = [
    # Directory paths
    (r'src/mcp_servers/pm_server/', 'mcp_server/'),
    (r'src/mcp_servers/', 'mcp_server/'),
    (r'src/pm_providers/', 'pm_providers/'),
    (r'src/server/', 'backend/server/'),
    (r'src/agents/', 'backend/agents/'),
    (r'src/analytics/', 'backend/analytics/'),
    (r'src/conversation/', 'backend/conversation/'),
    (r'src/graph/', 'backend/graph/'),
    (r'src/handlers/', 'backend/handlers/'),
    (r'src/llms/', 'backend/llms/'),
    (r'src/prompts/', 'backend/prompts/'),
    (r'src/rag/', 'backend/rag/'),
    (r'src/tools/', 'backend/tools/'),
    (r'src/utils/', 'backend/utils/'),
    (r'src/config/', 'backend/config/'),
    (r'src/crawler/', 'backend/crawler/'),
    (r'src/podcast/', 'backend/podcast/'),
    (r'src/ppt/', 'backend/ppt/'),
    (r'src/prose/', 'backend/prose/'),
    (r'src/prompt_enhancer/', 'backend/prompt_enhancer/'),
    (r'src/workflow.py', 'backend/workflow.py'),
    
    # Python import paths
    (r'from src\.mcp_servers\.pm_server', 'from mcp_server'),
    (r'from src\.mcp_servers', 'from mcp_server'),
    (r'from src\.pm_providers', 'from pm_providers'),
    (r'from src\.server', 'from backend.server'),
    (r'from src\.agents', 'from backend.agents'),
    (r'from src\.analytics', 'from backend.analytics'),
    (r'from src\.conversation', 'from backend.conversation'),
    (r'from src\.graph', 'from backend.graph'),
    (r'from src\.handlers', 'from backend.handlers'),
    (r'from src\.llms', 'from backend.llms'),
    (r'from src\.prompts', 'from backend.prompts'),
    (r'from src\.rag', 'from backend.rag'),
    (r'from src\.tools', 'from backend.tools'),
    (r'from src\.utils', 'from backend.utils'),
    (r'from src\.config', 'from backend.config'),
    (r'from src\.crawler', 'from backend.crawler'),
    (r'import src\.mcp_servers', 'import mcp_server'),
    (r'import src\.pm_providers', 'import pm_providers'),
    (r'import src\.server', 'import backend.server'),
    
    # Command examples
    (r'uvicorn src\.server\.app:app', 'uvicorn backend.server.app:app'),
    (r'uvicorn api\.main:app', 'uvicorn backend.server.app:app'),
    (r'python scripts/run_pm_mcp_server\.py', 'uv run python scripts/run_pm_mcp_server.py'),
    
    # File references in code blocks
    (r'`src/', '`backend/'),
    (r'`src\.', '`backend.'),
    (r'`mcp_servers/', '`mcp_server/'),
    (r'`pm_providers/', '`pm_providers/'),
]

def update_file(file_path: Path) -> bool:
    """Update a single markdown file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        updated = False
        
        # Apply all replacements
        for old_pattern, new_replacement in REPLACEMENTS:
            new_content = re.sub(old_pattern, new_replacement, content)
            if new_content != content:
                content = new_content
                updated = True
        
        # Only write if changes were made
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Update all markdown files"""
    project_root = Path(__file__).parent.parent
    
    # Directories to process
    directories = [
        project_root / 'docs',
        project_root,
        project_root / 'backend',
        project_root / 'mcp_server',
        project_root / 'pm_providers',
    ]
    
    updated_count = 0
    total_count = 0
    
    for directory in directories:
        if not directory.exists():
            print(f"Skipping {directory} (does not exist)")
            continue
        
        print(f"Processing {directory}...")
        for md_file in directory.rglob('*.md'):
            total_count += 1
            if update_file(md_file):
                updated_count += 1
                print(f"  Updated: {md_file.relative_to(project_root)}")
    
    print(f"\n✅ Updated {updated_count} out of {total_count} markdown files")

if __name__ == '__main__':
    main()

