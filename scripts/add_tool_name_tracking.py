#!/usr/bin/env python3
"""
Script to add tool name tracking to all tool registration functions.
"""

import re
import sys
from pathlib import Path

# Tool files to update
TOOL_FILES = [
    "src/mcp_servers/pm_server/tools/tasks.py",
    "src/mcp_servers/pm_server/tools/sprints.py",
    "src/mcp_servers/pm_server/tools/epics.py",
    "src/mcp_servers/pm_server/tools/users.py",
    "src/mcp_servers/pm_server/tools/analytics.py",
    "src/mcp_servers/pm_server/tools/task_interactions.py",
]

def extract_tool_name_from_function(func_def_line):
    """Extract tool name from function definition."""
    # Pattern: async def tool_name(arguments: ...
    match = re.search(r'async def (\w+)\(', func_def_line)
    if match:
        return match.group(1)
    return None

def add_tool_tracking(file_path):
    """Add tool name tracking after each tool_count += 1."""
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False
    
    content = file_path.read_text()
    lines = content.split('\n')
    
    new_lines = []
    i = 0
    modified = False
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Check if this is a tool_count += 1 line
        if re.match(r'\s*tool_count \+= 1\s*$', line):
            # Look backwards to find the function definition
            tool_name = None
            for j in range(i - 1, max(0, i - 50), -1):
                if 'async def' in lines[j] and 'arguments' in lines[j]:
                    tool_name = extract_tool_name_from_function(lines[j])
                    break
            
            if tool_name:
                # Add tool name tracking after tool_count += 1
                indent = len(line) - len(line.lstrip())
                tracking_line = ' ' * indent + f'if tool_names is not None:\n'
                tracking_line += ' ' * (indent + 4) + f'tool_names.append("{tool_name}")'
                tracking_line = tracking_line.format(tool_name=tool_name)
                new_lines.append(tracking_line)
                modified = True
                print(f"  Added tracking for: {tool_name}")
        
        i += 1
    
    if modified:
        file_path.write_text('\n'.join(new_lines))
        print(f"✅ Updated {file_path}")
        return True
    else:
        print(f"⚠️  No changes needed for {file_path}")
        return False

def main():
    """Main function."""
    print("Adding tool name tracking to all tool files...\n")
    
    updated = 0
    for tool_file in TOOL_FILES:
        print(f"Processing {tool_file}...")
        if add_tool_tracking(tool_file):
            updated += 1
        print()
    
    print(f"✅ Updated {updated}/{len(TOOL_FILES)} files")
    return 0 if updated > 0 else 1

if __name__ == "__main__":
    sys.exit(main())

