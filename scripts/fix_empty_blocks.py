#!/usr/bin/env python3
"""Fix all empty else/if blocks by adding pass statements."""
import re
import sys

def fix_empty_blocks(file_path: str):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    fixed = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check if this is an if/else/elif:
        if stripped.endswith(':') and (stripped.startswith('else') or stripped.startswith('if ') or stripped.startswith('elif ')):
            # Check if next line is empty or a comment or less/equal indentation
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_stripped = next_line.strip()
                
                # Get expected indentation for block content
                current_indent = len(line) - len(line.lstrip())
                expected_indent = current_indent + 4
                
                # Check if next non-empty line has less indentation (empty block)
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                
                if j < len(lines):
                    next_content = lines[j]
                    next_content_indent = len(next_content) - len(next_content.lstrip())
                    
                    # If next content line has <= current indentation, block is empty
                    if next_content_indent <= current_indent and next_content.strip():
                        # Insert pass with correct indentation
                        pass_line = ' ' * expected_indent + 'pass\n'
                        lines.insert(i + 1, pass_line)
                        fixed += 1
                        print(f"Fixed empty block at line {i + 1}")
        i += 1
    
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    return fixed

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "backend/graph/nodes.py"
    fixed = fix_empty_blocks(file_path)
    print(f"Fixed {fixed} empty blocks")
    
    # Verify syntax
    import py_compile
    try:
        py_compile.compile(file_path, doraise=True)
        print("✓ Syntax check passed")
    except py_compile.PyCompileError as e:
        print(f"✗ Syntax error: {e}")
