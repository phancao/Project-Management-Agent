#!/usr/bin/env python3
"""
Script to update imports in test files after restructuring
Changes src.* imports to backend.*, mcp_server.*, pm_providers.* imports
"""

import os
import re
from pathlib import Path

# Mapping of old imports to new imports for tests
IMPORT_MAPPINGS = [
    # Backend imports
    (r'from src\.server\.', 'from backend.server.'),
    (r'from src\.agents\.', 'from backend.agents.'),
    (r'from src\.graph\.', 'from backend.graph.'),
    (r'from src\.tools\.', 'from backend.tools.'),
    (r'from src\.analytics\.', 'from backend.analytics.'),
    (r'from src\.conversation\.', 'from backend.conversation.'),
    (r'from src\.handlers\.', 'from backend.handlers.'),
    (r'from src\.llms\.', 'from backend.llms.'),
    (r'from src\.rag\.', 'from backend.rag.'),
    (r'from src\.crawler\.', 'from backend.crawler.'),
    (r'from src\.config\.', 'from backend.config.'),
    (r'from src\.utils\.', 'from backend.utils.'),
    (r'from src\.prompt_enhancer\.', 'from backend.prompt_enhancer.'),
    (r'from src\.prompts\.', 'from backend.prompts.'),
    (r'import src\.server\.', 'import backend.server.'),
    (r'import src\.agents\.', 'import backend.agents.'),
    (r'import src\.graph\.', 'import backend.graph.'),
    (r'import src\.tools\.', 'import backend.tools.'),
    
    # MCP Server imports
    (r'from src\.mcp_servers\.pm_server\.', 'from mcp_server.'),
    (r'from src\.mcp_servers\.', 'from mcp_server.'),
    (r'import src\.mcp_servers\.', 'import mcp_server.'),
    
    # PM Provider imports
    (r'from src\.pm_providers\.', 'from pm_providers.'),
    (r'import src\.pm_providers\.', 'import pm_providers.'),
    
    # Patch decorators
    (r'@patch\("src\.server\.', '@patch("backend.server.'),
    (r'@patch\("src\.agents\.', '@patch("backend.agents.'),
    (r'@patch\("src\.graph\.', '@patch("backend.graph.'),
    (r'@patch\("src\.tools\.', '@patch("backend.tools.'),
    (r'@patch\("src\.mcp_servers\.', '@patch("mcp_server.'),
    (r'@patch\("src\.pm_providers\.', '@patch("pm_providers.'),
]

def update_file(file_path: Path) -> bool:
    """Update imports in a single test file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        updated = False
        
        # Apply all import mappings
        for old_pattern, new_replacement in IMPORT_MAPPINGS:
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
    """Update all test files"""
    project_root = Path(__file__).parent.parent
    
    # Directories to process
    directories = [
        project_root / 'tests' / 'backend',
        project_root / 'tests' / 'mcp_server',
        project_root / 'tests' / 'pm_providers',
        project_root / 'tests' / 'shared',
    ]
    
    updated_count = 0
    total_count = 0
    
    for directory in directories:
        if not directory.exists():
            print(f"Skipping {directory} (does not exist)")
            continue
        
        print(f"Processing {directory}...")
        for py_file in directory.rglob('*.py'):
            total_count += 1
            if update_file(py_file):
                updated_count += 1
                print(f"  Updated: {py_file.relative_to(project_root)}")
    
    print(f"\n✅ Updated {updated_count} out of {total_count} test files")

if __name__ == '__main__':
    main()

