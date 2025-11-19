#!/usr/bin/env python3
"""Run verification only for an existing import."""

import sys
import json
from pathlib import Path

# Add parent directory to path to import from import_work_packages
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.utils.import_work_packages import (
    parse_workbook,
    aggregate_workbook_rows,
    build_staging,
    OpenProjectClient,
    ConsoleUI,
    verify_import,
    report_verification,
    VERIFICATION_SOURCE,
)

def main():
    workbook_path = Path("assets/openproject/full Work Pakages - Intranet.xlsx")
    server_url = "http://localhost:8081"
    token_file = Path("/tmp/op13_token.txt")
    cache_path = Path("/tmp/staging-cache.json")
    
    if not token_file.exists():
        print(f"Error: Token file not found: {token_file}")
        print("Please run the import script first or provide a token.")
        return 1
    
    token = token_file.read_text().strip()
    
    if not cache_path.exists():
        print(f"Error: Staging cache not found: {cache_path}")
        print("Please run the import script first.")
        return 1
    
    # Build staging from workbook
    print("Loading workbook and building staging...")
    workbook_rows = parse_workbook(workbook_path)
    aggregated_tasks = aggregate_workbook_rows(workbook_rows)
    staging = build_staging(aggregated_tasks)
    
    # Load staging cache to populate openproject_id fields
    print("Loading staging cache...")
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            cache_payload = json.load(handle)
        cache_assignments = 0
        for key, entry in cache_payload.items():
            staged_task = staging.tasks.get(key)
            if staged_task:
                wp_id = entry.get("openproject_id")
                if wp_id:
                    staged_task.openproject_id = int(wp_id)
                    cache_assignments += 1
        print(f"  Loaded {cache_assignments} cached work package mapping(s).")
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  Failed to load cache: {exc}")
        return 1
    
    # Create client
    print(f"Connecting to OpenProject at {server_url}...")
    client = OpenProjectClient(server_url, token)
    
    # Fetch projects and populate staging project IDs
    print("Fetching projects from OpenProject...")
    project_records = client.list_projects()
    for staged_project in staging.projects.values():
        record = project_records.get(staged_project.name)
        if record:
            href = record["_links"]["self"]["href"]
            staged_project.openproject_id = int(href.split("/")[-1])
            print(f"  Mapped '{staged_project.name}' to project ID {staged_project.openproject_id}")
    
    # Create UI
    ui = ConsoleUI(auto_confirm=True)
    
    # Set verification source to use database
    global VERIFICATION_SOURCE
    VERIFICATION_SOURCE = "db"
    
    # Run verification
    ui.start_step("Verify import")
    verification = verify_import(
        workbook_path,
        client,
        staging,
        [],  # Empty list - we'll count all entries from staging
        ui,
        tracer=None,
        created_time_entry_ids=None,  # Check all entries
    )
    
    # Report results
    report_verification(verification, ui)
    
    ui.complete_step("Import verification completed.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

