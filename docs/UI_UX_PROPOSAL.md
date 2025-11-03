# UI/UX Proposal: Split-Panel Project Management Interface

## Overview

Design a JIRA-inspired split-panel interface with **Chat on Left** (40%) and **PM Views on Right** (60%). The system supports 18 core PM features organized into views.

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER (Fixed)                                                       │
│ 🦌 Project Management Agent | [👤 User] [⚙️ Settings] [🌙 Theme]   │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────┬──────────────────────────────────────────┐
│ CHAT PANEL (40%)        │ PM VIEW PANEL (60%)                       │
│                         │                                           │
│ ┌─────────────────────┐ │ ┌─────────────────────────────────────┐  │
│ │ Conversations       │ │ │ NAVIGATION TABS                      │  │
│ │ - AI Chat           │ │ │ [Dashboard] [Board] [Backlog] [Burndown]│
│ │ - Message List      │ │ └─────────────────────────────────────┘  │
│ │                     │ │                                           │
│ └─────────────────────┘ │ └─────────────────────────────────────┘  │
│                         │                                           │
│ ┌─────────────────────┐ │ ┌─────────────────────────────────────┐  │
│ │ Input Box           │ │ │ VIEW CONTENT                         │  │
│ │ [Type message...]   │ │ │ (Changes based on active tab)        │  │
│ │ [📎] [🚀 Send]      │ │ │                                       │  │
│ └─────────────────────┘ │ └─────────────────────────────────────┘  │
│                         │                                           │
└─────────────────────────┴──────────────────────────────────────────┘
```

---

## PM Views (JIRA-Inspired)

### 1. **Dashboard View** 📊

**Purpose**: Overview of projects, team workload, recent activity

**Layout**:
- **Top Stats**: Total projects, active sprints, open tasks, my tasks
- **My Work**: Cards showing tasks assigned to me by status
- **Team Activity**: Recent task updates, comments
- **Project Summary**: Quick project cards with progress
- **Upcoming Deadlines**: Tasks due in next 7 days

**Actions**:
- Click project → Switch to project + navigate to Backlog
- Click task → Switch to task + open detail panel
- Click user → Filter by assignee

---

### 2. **Sprint Board View** 🏃

**Purpose**: Kanban board for active sprint tasks

**Layout** (Columns):
```
┌─────────────────────────────────────────────────────────────────┐
│ Sprint: Sprint 1 [Sep 1 - Sep 15] | Capacity: 120h | Burndown: ████████░│
└─────────────────────────────────────────────────────────────────┘

┌──────────┬───────────┬───────────┬───────────┬──────────┐
│ To Do    │ In Progress│ Review    │ Done      │ Blocked  │
│ (8)      │ (3)       │ (2)      │ (5)       │ (1)     │
├──────────┼───────────┼───────────┼───────────┼──────────┤
│  [Task]  │  [Task]   │  [Task]   │  [Task]   │  [Task]  │
│  Priority │  Assignee │  Review   │  Done     │  Blocker │
│  ⏱️ 4h   │  ⏱️ 8h   │  ⏱️ 2h   │  ⏱️ 8h   │  ⏱️ 6h   │
├──────────┼───────────┼───────────┼───────────┼──────────┤
│  [Task]  │  [Task]   │  [Task]   │  [Task]   │          │
│  ...     │  ...      │  ...      │  ...      │          │
└──────────┴───────────┴───────────┴───────────┴──────────┘

Drag & drop between columns
Double-click task → Open detail panel
```

**Actions**:
- Drag & drop tasks between columns
- Click + to add task
- Click filter to show my tasks / all tasks
- Click sprint dropdown to switch sprints

---

### 3. **Backlog View** 📋

**Purpose**: All project tasks organized by priority

**Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Project: E-commerce Platform | [Filter: All / High / Medium / Low]│
├─────────────────────────────────────────────────────────────────┤
│ Priority Legend: 🔴 High | 🟡 Medium | 🔵 Low | ⚪ No Priority    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 🔴 HIGH PRIORITY (12 tasks)                                      │
├─────────────────────────────────────────────────────────────────┤
│ [☐] Setup CI/CD Pipeline            👤 John    ⏱️ 8h  📅 Due: Today│
│ [☐] Design Database Schema          👤 Sarah   ⏱️ 12h 📅 Due: Sep 3│
│ [☐] Implement Payment Gateway       👤 Mike    ⏱️ 16h 📅 Due: Sep 5│
├─────────────────────────────────────────────────────────────────┤
│ 🟡 MEDIUM PRIORITY (18 tasks)                                     │
│ [☐] Create User Stories             👤 Unassigned ⏱️ 4h           │
│ [☐] Setup Dev Environment           👤 Alice   ⏱️ 6h             │
├─────────────────────────────────────────────────────────────────┤
│ 🔵 LOW PRIORITY (5 tasks)                                         │
│ [☐] Write Documentation             👤 Unassigned ⏱️ 8h           │
└─────────────────────────────────────────────────────────────────┘

[+ Add Task] [Bulk Edit] [Move to Sprint]
```

**Actions**:
- Checkbox to mark complete
- Drag to reorder priority
- Click assignee to filter
- Drag to Sprint Board to assign
- Right-click for context menu

---

### 4. **Burndown Chart View** 📉

**Purpose**: Visualize sprint progress and velocity

**Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Sprint: Sprint 1 | Sep 1 - Sep 15 (2 weeks)                     │
│ Team: 5 people | Capacity: 120h | Planned: 100h                  │
└─────────────────────────────────────────────────────────────────┘

        Burndown Chart
        100│ ●────────●────────●─●──
          │ ●───────────────────── Ideal Line
          │ │
     Hours│ │
          │ │
         50│ │                    ●─── Actual
          │ │                ●────
          │ │         ●────────
          │ │  ●───────────────
          0└────────────────────────────────
           Day1   Day3  Day5  Day7  Day9  Day11 Day13
                         
    Velocity: 15h/day   Progress: 65%   Remaining: 35h

┌─────────────────────────────────────────────────────────────────┐
│ Task Breakdown By Status                                         │
│ ✅ Done: 45h (45%) | 🟡 In Progress: 30h (30%) | ⚪ To Do: 25h (25%)│
└─────────────────────────────────────────────────────────────────┘
```

**Actions**:
- Click sprint dropdown to view other sprints
- Hover chart for daily details
- Click task breakdown to filter board

---

### 5. **Timeline View** 📅

**Purpose**: Gantt-style timeline of sprints and milestones

**Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Timeline: E-commerce Platform                                    │
├──────────┬──────────────────────────────────────────────────────┤
│ Sprint 1 │████████████████████                                 │
│          │                      Sprint 2 │████████████████████│
│          │                                    │                │
│ Sep 1    │  Sep 7           Sep 15           │  Sep 22       │
│          │                                       Release      │
└──────────┴──────────────────────────────────────────────────────┘

Tasks:
┌──────────┬──────────────────────────────────────────────────────┐
│ Setup DB │ ████████                                             │
│ API Dev  │        ████████████████                             │
│ Frontend │                ████████████                         │
│ Testing  │                        ████████                     │
└──────────┴──────────────────────────────────────────────────────┘
```

---

### 6. **Team Assignments View** 👥

**Purpose**: Workload distribution across team

**Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Team Assignments: E-commerce Platform                           │
├─────────────────────────────────────────────────────────────────┤
│ 👤 John Doe                            Total: 45h | 75%         │
│   🔴 High: 8h    🟡 Medium: 24h   🔵 Low: 13h                  │
│   Tasks: 12 | Assigned: 10 | Completed: 2                       │
├─────────────────────────────────────────────────────────────────┤
│ 👤 Sarah Smith                          Total: 38h | 63%         │
│   🔴 High: 12h   🟡 Medium: 20h   🔵 Low: 6h                   │
│   Tasks: 10 | Assigned: 8 | Completed: 2                        │
├─────────────────────────────────────────────────────────────────┤
│ 👤 Mike Johnson                        Total: 52h | 87% ⚠️      │
│   🔴 High: 16h   🟡 Medium: 28h   🔵 Low: 8h                   │
│   Tasks: 13 | Assigned: 11 | Completed: 2                       │
├─────────────────────────────────────────────────────────────────┤
│ 👤 Alice Brown                          Total: 15h | 25%         │
│   Tasks: 5 | Assigned: 3 | Completed: 2                         │
└─────────────────────────────────────────────────────────────────┘

Workload Balance: ⚠️ Uneven (Mike overloaded, Alice underutilized)
```

---

## Context Switching (Hierarchical)

**Active Context Badges** (Top bar):
```
Active: [Project: E-commerce] [Sprint: Sprint 1] [Task: Setup DB]
```

**Chat Integration**:
- Type: "list my tasks" → Shows in Chat, Updates PM View to Backlog
- Type: "work on Sprint 1" → Switches context, Updates PM View to Board
- Type: "show burndown" → Updates PM View to Burndown Chart

---

## Responsive Design

**Desktop** (>1024px): 40/60 split
**Tablet** (768-1024px): 50/50 split or stackable
**Mobile** (<768px): Full chat, tab navigation for PM views

---

## Color Scheme (JIRA-Inspired)

- **Primary**: Blue (#0052CC)
- **Success**: Green (#00A86B)
- **Warning**: Orange (#FFAB00)
- **Error**: Red (#BF2600)
- **Text**: Dark Gray (#172B4D)
- **Background**: Light Gray (#F4F5F7)
- **Border**: Gray (#DFE1E6)

---

## Component Library

**Required Components**:
1. Task Card (with status, priority, assignee, time)
2. Sprint Board Columns (Kanban)
3. Backlog Item (with drag handles)
4. Burndown Chart (using Recharts or Chart.js)
5. Team Workload Bar
6. Context Badge
7. Project Selector
8. Detail Panel (slides from right)

**Tech Stack**:
- React 18 + Next.js 14
- TailwindCSS for styling
- DndKit for drag & drop
- Recharts for charts
- Framer Motion for animations
- Zustand for state management

---

## Implementation Phases

**Phase 1** (MVP):
- ✅ Split panel layout (fixed widths)
- ✅ Dashboard, Board, Backlog views
- ✅ Basic task cards
- ✅ Context switching

**Phase 2** (Enhancement):
- ✅ Burndown charts
- ✅ Drag & drop
- ✅ Team assignments
- ✅ Timeline view

**Phase 3** (Polish):
- ✅ Responsive design
- ✅ Animations
- ✅ Filters & search
- ✅ Bulk operations

---

## User Flows

### Flow 1: Create WBS & Plan Sprint
1. User types in Chat: "Create WBS for E-commerce Platform"
2. AI responds with progress in Chat
3. PM View switches to Dashboard → Shows new project
4. User types: "Plan 2 sprints"
5. PM View switches to Backlog → Shows tasks
6. User clicks Sprint Board → Drags tasks to columns

### Flow 2: Daily Standup
1. Open Dashboard → See "My Tasks" cards
2. Click Sprint 1 Board → See in-progress tasks
3. Log time via Chat: "log 4h for Setup DB"
4. View Burndown → See progress
5. Move completed tasks to Done

### Flow 3: Sprint Planning
1. Open Backlog → See all tasks
2. Drag tasks to Sprint Board → Assign to sprint
3. View Team Assignments → Check workload balance
4. Adjust as needed via Chat: "assign task X to John"
5. Review Timeline → Verify dates

---

## Next Steps

1. Create component mockups in Figma/Sketch
2. Build prototype in Next.js
3. Integrate with existing PM API
4. Add real-time updates via WebSockets
5. User testing & iteration

