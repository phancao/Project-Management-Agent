"""
Report Generator Handler

Generates project reports in various formats (markdown, PDF)
using project data and research findings.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    """Represents a section in the report"""
    title: str
    content: str
    level: int = 1


class ReportGenerator:
    """Generates project reports"""
    
    def __init__(self, db_session=None):
        """Initialize report generator
        
        Args:
            db_session: Database session for querying project data
        """
        self.db_session = db_session
    
    async def generate_report(
        self,
        project_id: str,
        report_type: str = "status",
        include_research: bool = True,
        format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate a report for a project
        
        Args:
            project_id: ID of the project
            report_type: Type of report (status, progress, summary, detailed)
            include_research: Whether to include research findings
            format: Output format (markdown, text, json)
            
        Returns:
            Dictionary containing report content and metadata
        """
        logger.info(f"Generating {report_type} report for project {project_id}")
        
        # Get project data
        project_data = await self._get_project_data(project_id)
        
        if not project_data:
            return {
                "error": f"Project {project_id} not found"
            }
        
        # Get research findings if requested
        research_data = None
        if include_research:
            research_data = await self._get_research_data(project_id)
        
        # Generate report based on type
        if report_type == "status":
            report_content = self._generate_status_report(project_data, research_data)
        elif report_type == "progress":
            report_content = self._generate_progress_report(project_data, research_data)
        elif report_type == "summary":
            report_content = self._generate_summary_report(project_data, research_data)
        elif report_type == "detailed":
            report_content = self._generate_detailed_report(project_data, research_data)
        else:
            report_content = self._generate_status_report(project_data, research_data)
        
        # Format report
        if format == "markdown":
            formatted_report = self._format_as_markdown(report_content)
        elif format == "text":
            formatted_report = self._format_as_text(report_content)
        elif format == "json":
            formatted_report = report_content
        else:
            formatted_report = self._format_as_markdown(report_content)
        
        return {
            "project_id": project_id,
            "project_name": project_data.get("name"),
            "report_type": report_type,
            "format": format,
            "generated_at": datetime.now().isoformat(),
            "content": formatted_report,
            "sections": len(report_content.get("sections", [])),
            "include_research": include_research
        }
    
    async def _get_project_data(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Fetch project data from database"""
        if not self.db_session:
            return None
        
        try:
            from database.crud import get_project, get_tasks_by_project, get_team_members_by_project
            from uuid import UUID
            from database.crud import get_user
            
            project = get_project(self.db_session, UUID(project_id))
            if not project:
                return None
            
            # Get tasks
            tasks = get_tasks_by_project(self.db_session, project.id)
            
            # Get team members
            team = get_team_members_by_project(self.db_session, project.id)
            team_names = []
            for member in team:
                user = get_user(self.db_session, member.user_id)
                if user:
                    team_names.append(user.name)
            
            # Calculate metrics
            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t.status == "completed")
            in_progress_tasks = sum(1 for t in tasks if t.status == "in_progress")
            total_hours = sum(t.estimated_hours for t in tasks if t.estimated_hours)
            completed_hours = sum(
                t.estimated_hours for t in tasks 
                if t.estimated_hours and t.status == "completed"
            )
            
            return {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "domain": project.domain,
                "priority": project.priority,
                "timeline_weeks": project.timeline_weeks,
                "budget": project.budget,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "team": team_names,
                "tasks": [
                    {
                        "id": str(t.id),
                        "title": t.title,
                        "description": t.description,
                        "status": t.status,
                        "priority": t.priority,
                        "estimated_hours": t.estimated_hours
                    }
                    for t in tasks
                ],
                "metrics": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "in_progress_tasks": in_progress_tasks,
                    "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                    "total_hours": total_hours,
                    "completed_hours": completed_hours,
                    "progress_percentage": (completed_hours / total_hours * 100) if total_hours > 0 else 0
                }
            }
        except Exception as e:
            logger.error(f"Error fetching project data: {e}")
            return None
    
    async def _get_research_data(self, project_id: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch research findings for the project"""
        if not self.db_session:
            return None
        
        try:
            from database.crud import get_research_sessions_by_project
            from uuid import UUID
            
            sessions = get_research_sessions_by_project(self.db_session, UUID(project_id))
            
            return [
                {
                    "topic": session.topic,
                    "research_type": session.research_type,
                    "created_at": session.created_at.isoformat() if session.created_at else None
                }
                for session in sessions
            ]
        except Exception as e:
            logger.error(f"Error fetching research data: {e}")
            return None
    
    def _generate_status_report(
        self, 
        project_data: Dict[str, Any], 
        research_data: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Generate a status report"""
        metrics = project_data.get("metrics", {})
        
        sections = [
            ReportSection(
                title="Executive Summary",
                content=f"""
# Executive Summary

**Project:** {project_data['name']}
**Status:** {project_data['status'].upper()}
**Priority:** {project_data['priority'].upper()}

## Key Metrics
- **Total Tasks:** {metrics['total_tasks']}
- **Completed:** {metrics['completed_tasks']} ({metrics['completion_rate']:.1f}%)
- **In Progress:** {metrics['in_progress_tasks']}
- **Overall Progress:** {metrics['progress_percentage']:.1f}% of estimated work completed
- **Team Size:** {len(project_data['team'])}
                """.strip(),
                level=1
            ),
            ReportSection(
                title="Current Status",
                content=f"""
# Current Status

## Tasks Breakdown
- ✅ **Completed:** {metrics['completed_tasks']} tasks
- 🔄 **In Progress:** {metrics['in_progress_tasks']} tasks
- ⏳ **To Do:** {metrics['total_tasks'] - metrics['completed_tasks'] - metrics['in_progress_tasks']} tasks

## Progress
Project is **{metrics['progress_percentage']:.1f}%** complete based on estimated hours.

**Completed Hours:** {metrics['completed_hours']:.1f}h / {metrics['total_hours']:.1f}h
                """.strip(),
                level=1
            ),
        ]
        
        if project_data.get('team'):
            sections.append(ReportSection(
                title="Team",
                content=f"# Team\n\n" + "\n".join(f"- {member}" for member in project_data['team']),
                level=1
            ))
        
        if research_data:
            sections.append(ReportSection(
                title="Research Findings",
                content=f"# Research Findings\n\n" + f"\n\nFound {len(research_data)} research sessions",
                level=1
            ))
        
        return {"type": "status", "sections": sections}
    
    def _generate_progress_report(
        self, 
        project_data: Dict[str, Any], 
        research_data: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Generate a detailed progress report"""
        # Start with status report
        sections = self._generate_status_report(project_data, research_data)["sections"]
        
        # Add task details
        tasks = project_data.get("tasks", [])
        if tasks:
            sections.append(ReportSection(
                title="Task Details",
                content=self._format_tasks_section(tasks),
                level=1
            ))
        
        return {"type": "progress", "sections": sections}
    
    def _generate_summary_report(
        self, 
        project_data: Dict[str, Any], 
        research_data: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Generate a concise summary report"""
        return {
            "type": "summary",
            "sections": [
                ReportSection(
                    title="Project Summary",
                    content=f"""
# {project_data['name']}

**Description:** {project_data['description'] or 'No description available'}

**Status:** {project_data['status']}
**Priority:** {project_data['priority']}
**Domain:** {project_data['domain'] or 'N/A'}
**Timeline:** {project_data['timeline_weeks'] or 'N/A'} weeks
**Budget:** ${project_data['budget']:,.2f} if project_data['budget'] else 'N/A'

**Team:** {', '.join(project_data.get('team', []))}
**Progress:** {project_data['metrics']['progress_percentage']:.1f}% complete
                    """.strip(),
                    level=1
                )
            ]
        }
    
    def _generate_detailed_report(
        self, 
        project_data: Dict[str, Any], 
        research_data: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Generate a comprehensive detailed report"""
        # Combine all sections
        progress_report = self._generate_progress_report(project_data, research_data)
        summary_section = self._generate_summary_report(project_data, research_data)["sections"][0]
        
        # Insert summary at the beginning
        sections = [summary_section] + progress_report["sections"]
        
        return {"type": "detailed", "sections": sections}
    
    def _format_tasks_section(self, tasks: List[Dict[str, Any]]) -> str:
        """Format tasks list as markdown"""
        content = "# Task Details\n\n"
        
        # Group by status
        by_status = {}
        for task in tasks:
            status = task['status']
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(task)
        
        for status, task_list in by_status.items():
            status_emoji = {
                "completed": "✅",
                "in_progress": "🔄",
                "todo": "⏳",
                "blocked": "🚫"
            }.get(status, "📋")
            
            content += f"\n## {status_emoji} {status.upper()}\n\n"
            for task in task_list:
                priority_emoji = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(task['priority'], "⚪")
                
                hours = f"({task['estimated_hours']:.1f}h)" if task['estimated_hours'] else ""
                content += f"- {priority_emoji} **{task['title']}** {hours}\n"
                if task.get('description'):
                    content += f"  - {task['description']}\n"
        
        return content
    
    def _format_as_markdown(self, report: Dict[str, Any]) -> str:
        """Format report as markdown"""
        sections = report.get("sections", [])
        content = ""
        
        for section in sections:
            # Add section with appropriate heading level
            heading = "#" * section.level
            content += f"\n{heading} {section.title}\n\n"
            content += section.content + "\n\n"
        
        return content.strip()
    
    def _format_as_text(self, report: Dict[str, Any]) -> str:
        """Format report as plain text"""
        sections = report.get("sections", [])
        content = ""
        
        for section in sections:
            title_line = "=" * len(section.title)
            content += f"\n{section.title}\n{title_line}\n\n"
            
            # Convert markdown to plain text (simple conversion)
            text_content = section.content
            # Remove markdown headers
            text_content = text_content.replace("#", "")
            # Remove markdown bold
            text_content = text_content.replace("**", "")
            
            content += text_content + "\n\n"
        
        return content.strip()

