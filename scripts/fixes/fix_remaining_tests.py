#!/usr/bin/env python3
"""
Fix remaining API tests that are missing auth_headers
"""

def fix_remaining_tests():
    """Fix all remaining tests to include auth_headers"""
    
    # Read the test file
    with open('tests/test_api.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add auth_headers to functions that don't have it
    functions_to_fix = [
        'test_task_endpoints',
        'test_research_endpoints', 
        'test_knowledge_endpoints',
        'test_data_validation',
        'test_error_handling'
    ]
    
    for func_name in functions_to_fix:
        # Find the function and add auth_headers after client creation
        pattern = f'(async def {func_name}\\(\\):.*?client = TestClient\\(app\\))(.*?)(try:)'
        replacement = r'\1\n        auth_headers = {"Authorization": "Bearer mock_token"}\n\2\3'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write back
    with open('tests/test_api.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Remaining API tests fixed with auth_headers")

if __name__ == "__main__":
    import re
    fix_remaining_tests()
