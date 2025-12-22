# Web Frontend - Codebase Summary

## Overview
Next.js React frontend for PM Agent and Meeting Notes Agent.

## Purpose
Provide user interfaces for project management chat, analytics visualization, and meeting processing.

---

## Module Structure

```
web/src/app/
├── pm/                  # PM Agent UI
│   ├── chat/            # Main chat interface
│   │   ├── page.tsx     # Chat page
│   │   └── components/  # Chat components
│   │       ├── views/   # Analytics views
│   │       └── analysis-block.tsx
│   └── layout.tsx
├── meeting/             # Meeting Agent UI
│   ├── page.tsx         # Main meeting page
│   └── components/
│       ├── meeting-upload.tsx    # Drag-drop upload
│       ├── meeting-list.tsx      # Meeting list
│       ├── meeting-summary.tsx   # Summary display
│       └── action-items-view.tsx # Action items
├── api/                 # API routes
│   ├── pm/              # PM API endpoints
│   └── meetings/        # Meeting API endpoints
│       ├── route.ts     # List meetings
│       ├── upload/      # Upload endpoint
│       ├── process/     # Process endpoint
│       └── [meetingId]/ # Meeting-specific
└── settings/            # Settings pages
```

---

## Key Components

### PM Chat
- `chat/page.tsx` - Main PM agent chat interface
- `analysis-block.tsx` - Analytics visualization container
- `views/` - Chart components (burndown, velocity, distribution)

### Meeting UI
- `meeting/page.tsx` - Meeting page with tab navigation
- `meeting-upload.tsx` - Drag-drop file upload with progress
- `meeting-summary.tsx` - Summary, key points, sentiment
- `action-items-view.tsx` - Action items with task creation

### API Routes
- `POST /api/meetings/upload` - Upload meeting files
- `POST /api/meetings/process` - Process uploaded meeting
- `GET /api/meetings/[id]/summary` - Get meeting summary
- `GET /api/meetings/[id]/action-items` - Get action items
- `POST /api/meetings/[id]/create-task` - Create PM task

---

## Tech Stack
- Next.js 14+ (App Router)
- React 18+
- TypeScript
- Tailwind CSS (if used)
- react-dropzone (file upload)
- Chart.js / Recharts (analytics)

---

## Running

```bash
cd web
npm install
npm run dev    # Development
npm run build  # Production build
```

---

## Environment Variables
- `NEXT_PUBLIC_API_URL` - Backend API URL
- `MCP_MEETING_SERVER_URL` - Meeting MCP server URL
