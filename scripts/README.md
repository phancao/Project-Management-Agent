# Scripts Directory

This directory contains all utility, maintenance, and helper scripts for the Project Management Agent project.

## Directory Structure

```
scripts/
├── README.md              # This file
├── dev/                   # Development helper scripts
│   ├── README.md
│   ├── start_backend_with_logs.sh
│   └── tail_backend_logs.sh
├── fixes/                 # Fix/repair scripts
│   ├── README.md
│   ├── fix_api_tests.py
│   ├── fix_jira_token.py
│   ├── fix_openproject_auth.py
│   └── fix_remaining_tests.py
├── tests/                 # Standalone test scripts
│   ├── README.md
│   └── test_*.py
└── utils/                 # Utility scripts
    ├── README.md
    ├── add_providers_from_env.py
    ├── check_api_key.py
    ├── check_jira_provider.py
    ├── check_openproject_provider.py
    ├── check_providers.py
    ├── cleanup_db.py
    ├── update_jira_email.py
    ├── update_jira_provider.py
    ├── update_openproject_api_key.py
    └── update_openproject_key.py
```

## Categories

### `dev/` - Development Helper Scripts
Scripts for development workflow, logging, and debugging.

### `fixes/` - Fix/Repair Scripts
One-time scripts used to fix specific issues in the codebase.

### `tests/` - Standalone Test Scripts
Manual testing, debugging, and validation scripts (not part of official test suite).

### `utils/` - Utility Scripts
General utility scripts for maintenance, setup, and configuration management.

## Usage

All scripts should be run from the project root:

```bash
# Utility scripts
python scripts/utils/check_providers.py

# Fix scripts
python scripts/fixes/fix_openproject_auth.py

# Development scripts
bash scripts/dev/start_backend_with_logs.sh

# Test scripts
python scripts/tests/test_openproject_all_pagination.py
```

## Guidelines

- **Keep scripts organized**: Place scripts in the appropriate subdirectory
- **Document scripts**: Add docstrings and comments explaining purpose
- **Update paths**: Scripts should work when run from project root
- **Clean up**: Remove temporary fix scripts after issues are resolved

## Core Application Files

The following files remain in the project root (not in scripts/):
- `main.py` - Main application entry point
- `server.py` - Server entry point
- `run_tests.py` - Test runner
- `quick_test.py` - Quick test script
- `bootstrap.sh` / `bootstrap.bat` - Bootstrap scripts

