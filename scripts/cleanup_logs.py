#!/usr/bin/env python3
"""
Safe Logger Cleanup Script v2

Removes logger.info/warning/debug calls and adds 'pass' to empty blocks.
"""
import re
import sys
from pathlib import Path


def remove_logger_calls(file_path: str, dry_run: bool = False) -> tuple[int, str]:
    """Remove logger calls safely, handling empty blocks."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    original_count = len(lines)
    new_lines = []
    i = 0
    removed = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check if this is a logger.info/warning/debug call
        if re.match(r'logger\.(info|warning|debug)\(', stripped):
            # Get indentation
            indent = len(line) - len(line.lstrip())
            
            # Count parentheses to find the complete statement
            paren_count = line.count('(') - line.count(')')
            removed += 1
            
            if paren_count == 0:
                # Single line - skip it
                i += 1
            else:
                # Multiline - skip until balanced
                while paren_count > 0 and i + 1 < len(lines):
                    i += 1
                    paren_count += lines[i].count('(') - lines[i].count(')')
                    removed += 1
                i += 1
            
            # Check if next non-empty line has less/same indentation (block would be empty)
            # Look ahead to see if we need a pass statement
            if new_lines and new_lines[-1].strip().endswith(':'):
                # Previous line ends with colon, this block might be empty now
                # Check next line's indentation
                next_i = i
                while next_i < len(lines) and not lines[next_i].strip():
                    next_i += 1
                
                if next_i < len(lines):
                    next_indent = len(lines[next_i]) - len(lines[next_i].lstrip())
                    prev_indent = len(new_lines[-1]) - len(new_lines[-1].lstrip())
                    
                    if next_indent <= prev_indent and lines[next_i].strip():
                        # Need to add pass
                        pass_indent = prev_indent + 4
                        new_lines.append(' ' * pass_indent + 'pass\n')
            
            continue
        
        new_lines.append(line)
        i += 1
    
    # Clean up multiple blank lines
    cleaned_lines = []
    prev_blank = False
    for line in new_lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        cleaned_lines.append(line)
        prev_blank = is_blank
    
    cleaned_content = ''.join(cleaned_lines)
    
    if not dry_run:
        with open(file_path, 'w') as f:
            f.write(cleaned_content)
    
    return original_count - len(cleaned_lines), cleaned_content


def main():
    if len(sys.argv) < 2:
        print("Usage: python cleanup_logs.py <file_path> [--dry-run]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    print(f"Processing: {file_path}")
    print(f"Dry run: {dry_run}")
    
    lines_removed, _ = remove_logger_calls(file_path, dry_run)
    
    print(f"Lines removed: {lines_removed}")
    
    # Verify syntax
    if not dry_run:
        import py_compile
        try:
            py_compile.compile(file_path, doraise=True)
            print("✓ Syntax check passed")
        except py_compile.PyCompileError as e:
            print(f"✗ Syntax error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
