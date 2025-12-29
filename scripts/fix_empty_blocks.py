#!/usr/bin/env python3
"""Fix all empty code blocks by adding pass statements."""
import sys
import os

def fix_empty_blocks(file_path: str):
    if not os.path.exists(file_path):
        return 0
        
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    keywords = ('if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally', 'with', 'def', 'class')
    
    fixed = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check if this line ends with a colon and starts with a keyword
        # Also handle multiline if/while/etc. by checking if it ends with ':'
        if stripped.endswith(':') and any(stripped.startswith(k) for k in keywords):
            # Find the next non-empty, non-comment line
            j = i + 1
            is_empty = True
            current_indent = len(line) - len(line.lstrip())
            
            while j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.strip()
                
                if not next_stripped or next_stripped.startswith('#'):
                    # Skip empty lines and comments
                    j += 1
                    continue
                
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent > current_indent:
                    # Found code inside the block
                    is_empty = False
                    break
                else:
                    # Found code at same or less indentation, so block is empty
                    is_empty = True
                    break
            
            # If we reached EOF without finding a block, it's empty
            if is_empty:
                expected_indent = current_indent + 4
                pass_line = ' ' * expected_indent + 'pass\n'
                lines.insert(i + 1, pass_line)
                fixed += 1
        i += 1
    
    if fixed > 0:
        with open(file_path, 'w') as f:
            f.writelines(lines)
    
    return fixed

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "backend/graph/nodes.py"
    fixed = fix_empty_blocks(file_path)
    print(f"Fixed {fixed} empty blocks in {file_path}")
    
    # Verify syntax
    import py_compile
    try:
        py_compile.compile(file_path, doraise=True)
        print("✓ Syntax check passed")
    except Exception as e:
        print(f"✗ Syntax error: {e}")
