#!/usr/bin/env python3
"""
Fix API tests to include authentication headers
"""

import re

def fix_api_tests():
    """Fix all API test endpoints to include auth headers"""
    
    # Read the test file
    with open('tests/test_api.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add auth headers to all client calls
    patterns = [
        # Fix client.get calls
        (r'client\.get\(([^)]+)\)', r'client.get(\1, headers=auth_headers)'),
        # Fix client.post calls  
        (r'client\.post\(([^)]+)\)', r'client.post(\1, headers=auth_headers)'),
        # Fix client.put calls
        (r'client\.put\(([^)]+)\)', r'client.put(\1, headers=auth_headers)'),
        # Fix client.delete calls
        (r'client\.delete\(([^)]+)\)', r'client.delete(\1, headers=auth_headers)'),
    ]
    
    # Apply patterns
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Fix duplicate headers issue
    content = content.replace('headers=auth_headers, headers=auth_headers', 'headers=auth_headers')
    
    # Write back
    with open('tests/test_api.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ API tests fixed with authentication headers")

if __name__ == "__main__":
    fix_api_tests()
