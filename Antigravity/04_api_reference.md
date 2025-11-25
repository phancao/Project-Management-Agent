# API Reference

> **Last Updated**: November 25, 2025  
> **Base URL**: `http://localhost:8000`

## 🔐 Authentication

Most endpoints require authentication via API key or JWT token.

```bash
# Using API key
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/pm/projects

# Using JWT token
curl -H "Authorization: Bearer your-jwt-token" http://localhost:8000/api/pm/projects
```

## 📡 Chat & Conversation Endpoints

### POST `/api/chat/stream`

Stream chat responses using Server-Sent Events (SSE).

**Request Body**:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Create a mobile app project"
    }
  ],
  "session_id": "optional-session-id",
  "max_plan_iterations": 3,
  "max_step_num": 10,
  "enable_clarification": true
}
```

**Response** (SSE Stream):
```
data: {"type": "message", "content": "I'll help you create a mobile app project..."}

data: {"type": "plan", "plan": {...}}

data: {"type": "step_start", "step": {...}}

data: {"type": "step_complete", "step": {...}}

data: [DONE]
```

**Event Types**:
- `message` - Agent message chunks
- `plan` - Research/execution plan
- `step_start` - Step execution started
- `step_complete` - Step execution completed
- `tool_call` - Tool invocation
- `error` - Error occurred

### GET `/api/chat/history/{session_id}`

Get chat history for a session.

**Response**:
```json
{
  "session_id": "abc-123",
  "messages": [
    {
      "role": "user",
      "content": "Create a project",
      "timestamp": "2025-11-25T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "I've created the project...",
      "timestamp": "2025-11-25T10:00:05Z"
    }
  ]
}
```

## 📋 Project Management Endpoints

### Projects

#### GET `/api/pm/projects`

List all projects from all active PM providers.

**Query Parameters**:
- `status` (optional) - Filter by status
- `provider_type` (optional) - Filter by provider type

**Response**:
```json
[
  {
    "id": "proj-123",
    "name": "Mobile App",
    "description": "iOS and Android app",
    "status": "active",
    "priority": "high",
    "start_date": "2025-11-01",
    "end_date": "2026-02-01",
    "provider_type": "openproject",
    "provider_id": "provider-1",
    "created_at": "2025-11-01T00:00:00Z",
    "updated_at": "2025-11-25T10:00:00Z"
  }
]
```

#### GET `/api/pm/projects/{project_id}`

Get a specific project.

**Response**:
```json
{
  "id": "proj-123",
  "name": "Mobile App",
  "description": "iOS and Android app",
  "status": "active",
  "priority": "high",
  "start_date": "2025-11-01",
  "end_date": "2026-02-01",
  "provider_type": "openproject",
  "provider_id": "provider-1",
  "created_at": "2025-11-01T00:00:00Z",
  "updated_at": "2025-11-25T10:00:00Z"
}
```

#### POST `/api/pm/projects`

Create a new project.

**Request Body**:
```json
{
  "name": "New Project",
  "description": "Project description",
  "status": "active",
  "priority": "medium",
  "start_date": "2025-12-01",
  "end_date": "2026-03-01"
}
```

**Response**: Created project object (201 Created)

#### PUT `/api/pm/projects/{project_id}`

Update a project.

**Request Body**: Partial project object

**Response**: Updated project object

#### DELETE `/api/pm/projects/{project_id}`

Delete a project.

**Response**: 204 No Content

### Tasks

#### GET `/api/pm/tasks`

List all tasks (optionally filtered by project).

**Query Parameters**:
- `project_id` (optional) - Filter by project
- `status` (optional) - Filter by status
- `assignee_id` (optional) - Filter by assignee
- `sprint_id` (optional) - Filter by sprint

**Response**:
```json
[
  {
    "id": "task-456",
    "title": "Implement login",
    "description": "User authentication",
    "project_id": "proj-123",
    "status": "in_progress",
    "priority": "high",
    "assignee_id": "user-789",
    "sprint_id": "sprint-1",
    "estimated_hours": 8.0,
    "actual_hours": 5.5,
    "created_at": "2025-11-20T00:00:00Z",
    "updated_at": "2025-11-25T10:00:00Z"
  }
]
```

#### POST `/api/pm/projects/{project_id}/tasks`

Create a new task in a project.

**Request Body**:
```json
{
  "title": "New Task",
  "description": "Task description",
  "priority": "medium",
  "status": "todo",
  "assignee_id": "user-789",
  "estimated_hours": 4.0
}
```

**Response**: Created task object (201 Created)

#### PUT `/api/pm/tasks/{task_id}`

Update a task.

**Request Body**: Partial task object

**Response**: Updated task object

#### POST `/api/pm/tasks/{task_id}/assign`

Assign a task to a user.

**Request Body**:
```json
{
  "assignee_id": "user-789"
}
```

**Response**: Updated task object

### Sprints

#### GET `/api/pm/sprints`

List all sprints (optionally filtered by project).

**Query Parameters**:
- `project_id` (optional) - Filter by project
- `status` (optional) - Filter by status

**Response**:
```json
[
  {
    "id": "sprint-1",
    "name": "Sprint 1",
    "project_id": "proj-123",
    "start_date": "2025-11-01",
    "end_date": "2025-11-14",
    "capacity_hours": 80.0,
    "planned_hours": 75.0,
    "status": "active",
    "created_at": "2025-11-01T00:00:00Z"
  }
]
```

#### POST `/api/pm/projects/{project_id}/sprints`

Create a new sprint.

**Request Body**:
```json
{
  "name": "Sprint 2",
  "start_date": "2025-11-15",
  "end_date": "2025-11-28",
  "capacity_hours": 80.0
}
```

**Response**: Created sprint object (201 Created)

### Users

#### GET `/api/pm/users`

List all users from PM providers.

**Response**:
```json
[
  {
    "id": "user-789",
    "name": "John Doe",
    "email": "john@example.com",
    "role": "developer",
    "provider_type": "openproject"
  }
]
```

## 📊 Analytics Endpoints

### GET `/api/analytics/projects/{project_id}/burndown`

Get burndown chart data for a sprint.

**Query Parameters**:
- `sprint_id` (required) - Sprint ID

**Response**:
```json
{
  "chart_type": "burndown",
  "title": "Sprint 1 Burndown",
  "data": {
    "dates": ["2025-11-01", "2025-11-02", "2025-11-03"],
    "ideal": [80, 70, 60],
    "actual": [80, 72, 65]
  },
  "metadata": {
    "sprint_id": "sprint-1",
    "total_hours": 80,
    "remaining_hours": 65
  },
  "generated_at": "2025-11-25T10:00:00Z"
}
```

### GET `/api/analytics/projects/{project_id}/velocity`

Get team velocity chart.

**Query Parameters**:
- `sprint_count` (optional, default: 6) - Number of sprints

**Response**:
```json
{
  "chart_type": "velocity",
  "title": "Team Velocity",
  "data": {
    "sprints": ["Sprint 1", "Sprint 2", "Sprint 3"],
    "planned": [80, 75, 85],
    "completed": [75, 70, 80]
  },
  "metadata": {
    "average_velocity": 75.0
  },
  "generated_at": "2025-11-25T10:00:00Z"
}
```

### GET `/api/analytics/sprints/{sprint_id}/report`

Get comprehensive sprint report.

**Response**:
```json
{
  "chart_type": "sprint_report",
  "title": "Sprint 1 Report",
  "data": {
    "completed_tasks": 12,
    "incomplete_tasks": 3,
    "total_hours_planned": 80,
    "total_hours_completed": 75,
    "completion_rate": 0.8
  },
  "metadata": {
    "sprint_id": "sprint-1",
    "start_date": "2025-11-01",
    "end_date": "2025-11-14"
  },
  "generated_at": "2025-11-25T10:00:00Z"
}
```

### GET `/api/analytics/projects/{project_id}/cfd`

Get Cumulative Flow Diagram data.

**Response**:
```json
{
  "chart_type": "cfd",
  "title": "Cumulative Flow Diagram",
  "data": {
    "dates": ["2025-11-01", "2025-11-02"],
    "todo": [20, 18],
    "in_progress": [5, 7],
    "done": [0, 2]
  },
  "generated_at": "2025-11-25T10:00:00Z"
}
```

### GET `/api/analytics/projects/{project_id}/cycle-time`

Get cycle time analysis.

**Response**:
```json
{
  "chart_type": "cycle_time",
  "title": "Cycle Time Analysis",
  "data": {
    "tasks": ["Task 1", "Task 2"],
    "cycle_times": [3.5, 4.2]
  },
  "metadata": {
    "average_cycle_time": 3.85,
    "median_cycle_time": 3.5
  },
  "generated_at": "2025-11-25T10:00:00Z"
}
```

## 🔧 Provider Management Endpoints

### GET `/api/pm/providers`

List all configured PM provider connections.

**Query Parameters**:
- `include_credentials` (optional, default: false) - Include API keys/tokens

**Response**:
```json
[
  {
    "id": "provider-1",
    "name": "OpenProject Main",
    "provider_type": "openproject",
    "base_url": "http://localhost:8082",
    "is_active": true,
    "created_at": "2025-11-01T00:00:00Z"
  }
]
```

### POST `/api/pm/providers`

Create a new PM provider connection.

**Request Body**:
```json
{
  "name": "JIRA Cloud",
  "provider_type": "jira",
  "base_url": "https://yourcompany.atlassian.net",
  "api_token": "your-jira-api-token",
  "username": "your-email@example.com"
}
```

**Response**: Created provider object (201 Created)

### PUT `/api/pm/providers/{provider_id}`

Update a provider connection.

**Request Body**: Partial provider object

**Response**: Updated provider object

### DELETE `/api/pm/providers/{provider_id}`

Delete a provider connection.

**Response**: 204 No Content

## 🏥 Health & Status Endpoints

### GET `/health`

Check API health status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-25T10:00:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "mcp_server": "healthy"
  }
}
```

### GET `/config`

Get server configuration (public settings only).

**Response**:
```json
{
  "version": "2.0.0",
  "environment": "production",
  "features": {
    "chat": true,
    "analytics": true,
    "mcp": true
  }
}
```

## 🔌 WebSocket Events

### Connection

```javascript
const socket = io('http://localhost:8000');

socket.on('connect', () => {
  console.log('Connected to WebSocket');
});
```

### Events

#### `task_updated`
Emitted when a task is updated.

```javascript
socket.on('task_updated', (data) => {
  console.log('Task updated:', data);
  // data: { task_id, project_id, changes }
});
```

#### `project_updated`
Emitted when a project is updated.

```javascript
socket.on('project_updated', (data) => {
  console.log('Project updated:', data);
  // data: { project_id, changes }
});
```

#### `sprint_updated`
Emitted when a sprint is updated.

```javascript
socket.on('sprint_updated', (data) => {
  console.log('Sprint updated:', data);
  // data: { sprint_id, project_id, changes }
});
```

## 📝 Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-11-25T10:00:00Z"
}
```

**Common HTTP Status Codes**:
- `200` - Success
- `201` - Created
- `204` - No Content
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

---

**Next**: [Deployment Guide →](./05_deployment_guide.md)
