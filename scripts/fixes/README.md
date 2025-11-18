# Fix/Repair Scripts

This directory contains scripts used to fix or repair issues in the codebase.

## Scripts

- `fix_api_tests.py` - Fix API test issues
- `fix_jira_token.py` - Fix JIRA token configuration
- `fix_openproject_auth.py` - Fix OpenProject authentication
- `fix_remaining_tests.py` - Fix remaining test issues

## Usage

Run scripts from the project root:

```bash
# From project root
python scripts/fixes/fix_openproject_auth.py
```

Or from within this directory:

```bash
cd scripts/fixes
python fix_openproject_auth.py
```

## Notes

- These scripts are typically one-time fixes for specific issues
- They may modify code or configuration files
- Review the script before running to understand what it does
- Consider removing scripts after the issue is resolved

