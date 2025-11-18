# Utility Scripts

This directory contains utility scripts for managing and maintaining the Project Management Agent.

## Scripts

### Provider Management
- `add_providers_from_env.py` - Add providers from environment variables
- `check_providers.py` - Check configured providers
- `check_jira_provider.py` - Check JIRA provider configuration
- `check_openproject_provider.py` - Check OpenProject provider configuration
- `update_jira_provider.py` - Update JIRA provider settings
- `update_openproject_api_key.py` - Update OpenProject API key
- `update_openproject_key.py` - Update OpenProject key
- `update_jira_email.py` - Update JIRA email

### Database Utilities
- `cleanup_db.py` - Clean up database

### API Utilities
- `check_api_key.py` - Check API key validity

## Usage

Run scripts from the project root:

```bash
# From project root
python scripts/utils/check_providers.py
python scripts/utils/cleanup_db.py
```

Or from within this directory:

```bash
cd scripts/utils
python check_providers.py
```

## Notes

- These scripts are utility tools for maintenance and setup
- They may require environment variables or database access
- Check individual script docstrings for specific usage instructions

