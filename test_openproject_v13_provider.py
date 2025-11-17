#!/usr/bin/env python3
"""
Comprehensive Test Script for OpenProject v13 Provider

Tests all functions of the OpenProjectV13Provider to ensure compatibility
with OpenProject v13.4.1 API.

Usage:
    python test_openproject_v13_provider.py <base_url> <api_key> [project_id]
    
Example:
    python test_openproject_v13_provider.py http://localhost:8081 your_api_key 123
"""

import asyncio
import sys
import os
from typing import Optional, Dict, Any, List
from datetime import date, datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pm_providers.openproject_v13 import OpenProjectV13Provider
from src.pm_providers.models import (
    PMProviderConfig, PMProject, PMTask, PMSprint, PMEpic, PMUser
)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results: List[Dict[str, Any]] = []
    
    def add_result(self, test_name: str, passed: bool, message: str = "", warning: bool = False):
        """Add a test result"""
        if warning:
            self.warnings += 1
            status = "WARNING"
        elif passed:
            self.passed += 1
            status = "PASS"
        else:
            self.failed += 1
            status = "FAIL"
        
        self.results.append({
            "test": test_name,
            "status": status,
            "message": message
        })
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{Colors.BOLD}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}Test Summary{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.GREEN}✅ Passed: {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}❌ Failed: {self.failed}{Colors.RESET}")
        if self.warnings > 0:
            print(f"{Colors.YELLOW}⚠️  Warnings: {self.warnings}{Colors.RESET}")
        print(f"\nTotal: {self.passed + self.failed + self.warnings}")
        print(f"{Colors.BOLD}{'=' * 80}{Colors.RESET}\n")
        
        # Print detailed results
        for result in self.results:
            if result["status"] == "PASS":
                print(f"{Colors.GREEN}✅ {result['test']}{Colors.RESET}")
            elif result["status"] == "FAIL":
                print(f"{Colors.RED}❌ {result['test']}: {result['message']}{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}⚠️  {result['test']}: {result['message']}{Colors.RESET}")


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


async def test_health_check(provider: OpenProjectV13Provider, results: TestResults):
    """Test health check"""
    print_header("1. Health Check")
    try:
        is_healthy = await provider.health_check()
        if is_healthy:
            results.add_result("Health Check", True, "Provider is healthy")
            print(f"{Colors.GREEN}✅ Health check passed{Colors.RESET}")
        else:
            results.add_result("Health Check", False, "Provider is not healthy")
            print(f"{Colors.RED}❌ Health check failed{Colors.RESET}")
    except Exception as e:
        results.add_result("Health Check", False, str(e))
        print(f"{Colors.RED}❌ Health check error: {e}{Colors.RESET}")


async def test_projects(provider: OpenProjectV13Provider, results: TestResults):
    """Test project operations"""
    print_header("2. Project Operations")
    
    # List projects
    try:
        projects = await provider.list_projects()
        results.add_result("List Projects", True, f"Found {len(projects)} projects")
        print(f"{Colors.GREEN}✅ List projects: {len(projects)} found{Colors.RESET}")
        
        if projects:
            test_project = projects[0]
            project_id = test_project.id
            
            # Get project
            try:
                project = await provider.get_project(project_id)
                if project:
                    results.add_result("Get Project", True, f"Retrieved project {project_id}")
                    print(f"{Colors.GREEN}✅ Get project: {project.name}{Colors.RESET}")
                else:
                    results.add_result("Get Project", False, "Project not found")
            except Exception as e:
                results.add_result("Get Project", False, str(e))
    except Exception as e:
        results.add_result("List Projects", False, str(e))
        print(f"{Colors.RED}❌ List projects error: {e}{Colors.RESET}")


async def test_tasks(provider: OpenProjectV13Provider, project_id: Optional[str], results: TestResults):
    """Test task operations"""
    print_header("3. Task (Work Package) Operations")
    
    # List tasks
    try:
        tasks = await provider.list_tasks(project_id=project_id)
        results.add_result("List Tasks", True, f"Found {len(tasks)} tasks")
        print(f"{Colors.GREEN}✅ List tasks: {len(tasks)} found{Colors.RESET}")
        
        if tasks:
            test_task = tasks[0]
            task_id = test_task.id
            
            # Get task
            try:
                task = await provider.get_task(task_id)
                if task:
                    results.add_result("Get Task", True, f"Retrieved task {task_id}")
                    print(f"{Colors.GREEN}✅ Get task: {task.title[:50]}{Colors.RESET}")
                    
                    # Test update (non-destructive - just update description)
                    try:
                        updates = {"description": f"Test update at {datetime.now().isoformat()}"}
                        updated_task = await provider.update_task(task_id, updates)
                        if updated_task:
                            results.add_result("Update Task", True, "Task updated successfully")
                            print(f"{Colors.GREEN}✅ Update task: Success{Colors.RESET}")
                    except Exception as e:
                        results.add_result("Update Task", False, str(e))
                        print(f"{Colors.RED}❌ Update task error: {e}{Colors.RESET}")
                else:
                    results.add_result("Get Task", False, "Task not found")
            except Exception as e:
                results.add_result("Get Task", False, str(e))
    except Exception as e:
        results.add_result("List Tasks", False, str(e))
        print(f"{Colors.RED}❌ List tasks error: {e}{Colors.RESET}")


async def test_sprints(provider: OpenProjectV13Provider, project_id: Optional[str], results: TestResults):
    """Test sprint operations"""
    print_header("4. Sprint (Version) Operations")
    
    # List sprints
    try:
        sprints = await provider.list_sprints(project_id=project_id)
        results.add_result("List Sprints", True, f"Found {len(sprints)} sprints")
        print(f"{Colors.GREEN}✅ List sprints: {len(sprints)} found{Colors.RESET}")
        
        if sprints:
            test_sprint = sprints[0]
            sprint_id = test_sprint.id
            
            # Get sprint
            try:
                sprint = await provider.get_sprint(sprint_id)
                if sprint:
                    results.add_result("Get Sprint", True, f"Retrieved sprint {sprint_id}")
                    print(f"{Colors.GREEN}✅ Get sprint: {sprint.name}{Colors.RESET}")
                else:
                    results.add_result("Get Sprint", False, "Sprint not found")
            except Exception as e:
                results.add_result("Get Sprint", False, str(e))
    except Exception as e:
        results.add_result("List Sprints", False, str(e))
        print(f"{Colors.RED}❌ List sprints error: {e}{Colors.RESET}")


async def test_users(provider: OpenProjectV13Provider, results: TestResults):
    """Test user operations"""
    print_header("5. User Operations")
    
    # List users
    try:
        users = await provider.list_users()
        results.add_result("List Users", True, f"Found {len(users)} users")
        print(f"{Colors.GREEN}✅ List users: {len(users)} found{Colors.RESET}")
        
        if users:
            test_user = users[0]
            user_id = test_user.id
            
            # Get user
            try:
                user = await provider.get_user(user_id)
                if user:
                    results.add_result("Get User", True, f"Retrieved user {user_id}")
                    print(f"{Colors.GREEN}✅ Get user: {user.name}{Colors.RESET}")
                else:
                    results.add_result("Get User", False, "User not found")
            except Exception as e:
                results.add_result("Get User", False, str(e))
        
        # Get current user
        try:
            current_user = await provider.get_current_user()
            if current_user:
                results.add_result("Get Current User", True, f"Current user: {current_user.name}")
                print(f"{Colors.GREEN}✅ Get current user: {current_user.name}{Colors.RESET}")
            else:
                results.add_result("Get Current User", False, "Current user not found")
        except Exception as e:
            results.add_result("Get Current User", False, str(e))
    except Exception as e:
        results.add_result("List Users", False, str(e))
        print(f"{Colors.RED}❌ List users error: {e}{Colors.RESET}")


async def test_epics(provider: OpenProjectV13Provider, project_id: Optional[str], results: TestResults):
    """Test epic operations"""
    print_header("6. Epic Operations")
    
    # List epics
    try:
        epics = await provider.list_epics(project_id=project_id)
        results.add_result("List Epics", True, f"Found {len(epics)} epics")
        print(f"{Colors.GREEN}✅ List epics: {len(epics)} found{Colors.RESET}")
        
        if epics:
            test_epic = epics[0]
            epic_id = test_epic.id
            
            # Get epic
            try:
                epic = await provider.get_epic(epic_id)
                if epic:
                    results.add_result("Get Epic", True, f"Retrieved epic {epic_id}")
                    print(f"{Colors.GREEN}✅ Get epic: {epic.name[:50]}{Colors.RESET}")
                else:
                    results.add_result("Get Epic", False, "Epic not found")
            except Exception as e:
                results.add_result("Get Epic", False, str(e))
    except Exception as e:
        results.add_result("List Epics", False, str(e))
        print(f"{Colors.RED}❌ List epics error: {e}{Colors.RESET}")


async def test_statuses(provider: OpenProjectV13Provider, project_id: Optional[str], results: TestResults):
    """Test status operations"""
    print_header("7. Status Operations")
    
    try:
        statuses = await provider.list_statuses("task", project_id=project_id)
        results.add_result("List Statuses", True, f"Found {len(statuses)} statuses")
        print(f"{Colors.GREEN}✅ List statuses: {len(statuses)} found{Colors.RESET}")
        
        if statuses:
            print(f"   Sample statuses: {', '.join([s.get('name', '') for s in statuses[:5]])}")
    except Exception as e:
        results.add_result("List Statuses", False, str(e))
        print(f"{Colors.RED}❌ List statuses error: {e}{Colors.RESET}")


async def test_priorities(provider: OpenProjectV13Provider, project_id: Optional[str], results: TestResults):
    """Test priority operations"""
    print_header("8. Priority Operations")
    
    try:
        priorities = await provider.list_priorities(project_id=project_id)
        results.add_result("List Priorities", True, f"Found {len(priorities)} priorities")
        print(f"{Colors.GREEN}✅ List priorities: {len(priorities)} found{Colors.RESET}")
        
        if priorities:
            print(f"   Sample priorities: {', '.join([p.get('name', '') for p in priorities[:5]])}")
    except Exception as e:
        results.add_result("List Priorities", False, str(e))
        print(f"{Colors.RED}❌ List priorities error: {e}{Colors.RESET}")


async def test_labels(provider: OpenProjectV13Provider, project_id: Optional[str], results: TestResults):
    """Test label operations"""
    print_header("9. Label Operations")
    
    try:
        labels = await provider.list_labels(project_id=project_id)
        results.add_result("List Labels", True, f"Found {len(labels)} labels")
        print(f"{Colors.GREEN}✅ List labels: {len(labels)} found{Colors.RESET}")
    except Exception as e:
        results.add_result("List Labels", False, str(e))
        print(f"{Colors.RED}❌ List labels error: {e}{Colors.RESET}")


async def run_all_tests(base_url: str, api_key: str, project_id: Optional[str] = None):
    """Run all tests"""
    print_header("OpenProject v13 Provider Test Suite")
    print(f"Base URL: {base_url}")
    print(f"Project ID: {project_id or 'All projects'}")
    print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
    
    # Create provider
    config = PMProviderConfig(
        provider_type="openproject_v13",
        base_url=base_url,
        api_key=api_key
    )
    
    provider = OpenProjectV13Provider(config)
    results = TestResults()
    
    # Run tests
    await test_health_check(provider, results)
    await test_projects(provider, results)
    await test_tasks(provider, project_id, results)
    await test_sprints(provider, project_id, results)
    await test_users(provider, results)
    await test_epics(provider, project_id, results)
    await test_statuses(provider, project_id, results)
    await test_priorities(provider, project_id, results)
    await test_labels(provider, project_id, results)
    
    # Print summary
    results.print_summary()
    
    return results


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python test_openproject_v13_provider.py <base_url> <api_key> [project_id]")
        print("Example: python test_openproject_v13_provider.py http://localhost:8081 your_api_key 123")
        sys.exit(1)
    
    base_url = sys.argv[1]
    api_key = sys.argv[2]
    project_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Run tests
    results = asyncio.run(run_all_tests(base_url, api_key, project_id))
    
    # Exit with appropriate code
    if results.failed > 0:
        sys.exit(1)
    elif results.warnings > 0:
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

