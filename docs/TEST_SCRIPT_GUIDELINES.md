# Test Script Guidelines for AI Assistants

This document provides clear instructions for AI assistants on where to create test scripts in the Project Management Agent codebase.

## 📁 Directory Structure

```
Project-Management-Agent/
├── tests/                    # Official test suite (pytest)
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── test_*.py            # Main test files
│
└── scripts/
    └── tests/                # Standalone test scripts
        ├── README.md         # Guidelines for standalone scripts
        └── test_*.py         # Manual testing/debugging scripts
```

## 🎯 Decision Tree: Where to Create Test Scripts

### Use `scripts/tests/` for:
- ✅ **Standalone debugging scripts** - For investigating specific issues
- ✅ **Manual validation scripts** - For testing features manually
- ✅ **Comprehensive test scripts** - For thorough testing of complex features (e.g., pagination)
- ✅ **API integration validation** - For testing external API integrations
- ✅ **One-off test scripts** - Temporary scripts for specific debugging needs
- ✅ **Scripts that require manual setup** - Scripts needing API keys, database connections, etc.

**Example**: `scripts/tests/test_openproject_all_pagination.py`

### Use `tests/` for:
- ✅ **Unit tests** - Testing individual functions/classes
- ✅ **Integration tests** - Testing component interactions
- ✅ **Automated test suite** - Tests that run in CI/CD
- ✅ **Pytest-compatible tests** - Tests using pytest framework
- ✅ **Tests with fixtures** - Tests using pytest fixtures
- ✅ **Tests with assertions** - Tests using pytest assertions

**Example**: `tests/unit/server/test_app.py`

## 📝 Naming Conventions

### Standalone Test Scripts (`scripts/tests/`)
- Format: `test_<feature>_<purpose>.py`
- Examples:
  - `test_openproject_all_pagination.py`
  - `test_jira_auth_validation.py`
  - `test_clickup_endpoints_debug.py`

### Official Test Suite (`tests/`)
- Format: `test_<module>_<feature>.py` or `test_<feature>.py`
- Examples:
  - `tests/unit/server/test_app.py`
  - `tests/integration/test_workflow.py`
  - `tests/test_pm_features.py`

## 🔧 Template for Standalone Test Scripts

When creating a new standalone test script in `scripts/tests/`, use this template:

```python
#!/usr/bin/env python3
"""
Test script for [Feature Name]

Purpose: [What this script tests]
Usage: python scripts/tests/test_<feature>.py
Dependencies: [List any special requirements]
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Your imports here
# from src.pm_providers.openproject_v13 import OpenProjectV13Provider

def main():
    """Main test function"""
    print("Testing [feature]...")
    try:
        # Your test implementation here
        print("✅ All tests passed!")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

## 🔧 Template for Official Test Suite

When creating a new test in `tests/`, use this template:

```python
"""
Unit tests for [Module Name]

Tests the [feature/component] functionality.
"""

import pytest
from src.module import ClassOrFunction

class TestFeature:
    """Test suite for [feature]"""
    
    def test_basic_functionality(self):
        """Test basic functionality"""
        # Arrange
        # Act
        # Assert
        assert True
    
    def test_edge_case(self):
        """Test edge case"""
        # Test implementation
        pass
```

## ✅ Checklist Before Creating Test Scripts

Before creating a test script, ask:

1. **Is this for automated testing?**
   - ✅ Yes → Use `tests/` directory
   - ❌ No → Use `scripts/tests/` directory

2. **Will this run in CI/CD?**
   - ✅ Yes → Use `tests/` directory
   - ❌ No → Use `scripts/tests/` directory

3. **Does this require manual setup (API keys, etc.)?**
   - ✅ Yes → Use `scripts/tests/` directory
   - ❌ No → Could use either, but prefer `tests/` if automated

4. **Is this a one-off debugging script?**
   - ✅ Yes → Use `scripts/tests/` directory
   - ❌ No → Consider `tests/` directory

5. **Does this use pytest fixtures/assertions?**
   - ✅ Yes → Use `tests/` directory
   - ❌ No → Could use `scripts/tests/` directory

## 📚 Additional Resources

- **Standalone Scripts**: See `scripts/tests/README.md` for detailed guidelines
- **Official Test Suite**: See `TESTING_GUIDE.md` for testing best practices
- **Pytest Documentation**: https://docs.pytest.org/

## 🚨 Important Notes

1. **Never create test scripts in the project root** - Always use `scripts/tests/` or `tests/`
2. **Standalone scripts are not included in CI/CD** - They are for manual testing only
3. **Keep scripts organized** - Use clear naming and documentation
4. **Clean up temporary scripts** - Remove one-off debugging scripts when no longer needed

## 💡 Examples

### Example 1: Standalone Pagination Test
**Location**: `scripts/tests/test_openproject_all_pagination.py`
**Reason**: Comprehensive manual test for pagination, requires API keys, not part of automated suite

### Example 2: Unit Test for API Endpoint
**Location**: `tests/unit/server/test_app.py`
**Reason**: Automated unit test using pytest, part of CI/CD pipeline

### Example 3: Integration Test for Workflow
**Location**: `tests/integration/test_workflow.py`
**Reason**: Automated integration test using pytest, part of CI/CD pipeline

### Example 4: Debug Script for Auth Issue
**Location**: `scripts/tests/test_openproject_auth_debug.py`
**Reason**: One-off debugging script, requires manual setup, not automated

---

**Last Updated**: 2024
**Maintained By**: Project Management Agent Team

