#!/usr/bin/env python3
"""
Script to update imports after restructuring
Changes src.* imports to backend.* imports
"""

import os
import re
from pathlib import Path

# Mapping of old imports to new imports
IMPORT_MAPPINGS = {
    # Backend imports
    r'from src\.config\.': 'from backend.config.',
    r'from src\.graph\.': 'from backend.graph.',
    r'from src\.llms\.': 'from backend.llms.',
    r'from src\.podcast\.': 'from backend.podcast.',
    r'from src\.ppt\.': 'from backend.ppt.',
    r'from src\.prompt_enhancer\.': 'from backend.prompt_enhancer.',
    r'from src\.prose\.': 'from backend.prose.',
    r'from src\.rag\.': 'from backend.rag.',
    r'from src\.server\.': 'from backend.server.',
    r'from src\.tools\.': 'from backend.tools.',
    r'from src\.utils\.': 'from backend.utils.',
    r'from src\.agents\.': 'from backend.agents.',
    r'from src\.analytics\.': 'from backend.analytics.',
    r'from src\.conversation\.': 'from backend.conversation.',
    r'from src\.handlers\.': 'from backend.handlers.',
    r'from src\.crawler\.': 'from backend.crawler.',
    r'import src\.config\.': 'import backend.config.',
    r'import src\.graph\.': 'import backend.graph.',
    r'import src\.llms\.': 'import backend.llms.',
    r'import src\.server\.': 'import backend.server.',
    r'import src\.tools\.': 'import backend.tools.',
    r'import src\.utils\.': 'import backend.utils.',
    
    # PM Providers - already moved, but update if any references remain
    r'from src\.pm_providers\.': 'from pm_providers.',
    r'import src\.pm_providers\.': 'import pm_providers.',
    
    # MCP Server - update if any references
    r'from src\.mcp_servers\.': 'from mcp_server.',
    r'import src\.mcp_servers\.': 'import mcp_server.',
}

def update_file_imports(file_path: Path) -> bool:
    """Update imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        updated = False
        
        # Apply all import mappings
        for old_pattern, new_replacement in IMPORT_MAPPINGS.items():
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
    """Update imports in all Python files"""
    project_root = Path(__file__).parent.parent
    
    # Directories to process
    directories = [
        project_root / 'backend',
        project_root / 'mcp_server',
        project_root / 'pm_providers',
        project_root / 'scripts',
        project_root / 'tests',
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
            if update_file_imports(py_file):
                updated_count += 1
                print(f"  Updated: {py_file.relative_to(project_root)}")
    
    print(f"\n✅ Updated {updated_count} out of {total_count} files")

if __name__ == '__main__':
    main()

