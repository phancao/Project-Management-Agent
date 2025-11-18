# Standalone Test Scripts

This directory contains standalone test scripts used for manual testing, debugging, and validation of specific features or components.

## Purpose

These scripts are **not part of the official test suite** (which is located in `tests/` directory). Instead, they are:

- **Manual testing scripts**: For ad-hoc testing of specific features
- **Debugging tools**: For investigating issues or validating fixes
- **Integration validation**: For testing external API integrations
- **Comprehensive tests**: For thorough testing of complex features (e.g., pagination)

## Structure

```
scripts/tests/
├── README.md                          # This file
├── test_openproject_all_pagination.py # Comprehensive pagination test
└── ...                                # Other standalone test scripts
```

## Usage

Run these scripts directly from the project root:

```bash
# From project root
python scripts/tests/test_openproject_all_pagination.py
```

Or from within the scripts/tests directory:

```bash
cd scripts/tests
python test_openproject_all_pagination.py
```

## Guidelines for Creating New Test Scripts

When creating new standalone test scripts:

1. **Place them here**: All standalone test scripts should be created in `scripts/tests/`
2. **Naming convention**: Use `test_<feature>_<purpose>.py` format
   - Example: `test_openproject_pagination.py`
   - Example: `test_jira_auth_validation.py`
3. **Documentation**: Add a docstring at the top explaining:
   - What the script tests
   - How to run it
   - What dependencies it needs
4. **Self-contained**: Scripts should be runnable independently
5. **Clear output**: Provide clear, readable output with success/failure indicators

## Examples

### Example Test Script Structure

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

# Your test code here
def main():
    """Main test function"""
    print("Testing [feature]...")
    # Test implementation
    print("✅ All tests passed!")

if __name__ == "__main__":
    main()
```

## Difference from Official Test Suite

| Aspect | Standalone Scripts (`scripts/tests/`) | Official Test Suite (`tests/`) |
|--------|--------------------------------------|--------------------------------|
| Purpose | Manual testing, debugging, validation | Automated unit/integration tests |
| Execution | Run manually when needed | Run via `pytest` or `run_tests.py` |
| Structure | Independent scripts | pytest-compatible test files |
| CI/CD | Not included | Included in CI/CD pipeline |
| Maintenance | As needed | Regularly maintained |

## Notes

- These scripts are **not** included in the automated test suite
- They may require manual setup (API keys, database connections, etc.)
- They are useful for development and debugging but not for CI/CD
- Keep them organized and documented for future reference

