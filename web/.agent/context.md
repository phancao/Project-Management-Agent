# Web Frontend - AI Context

## When to Use This Module
- Adding/modifying UI components
- Creating new pages or views
- Adding API routes
- Styling changes

## Quick Reference

### File Locations
| Need | Location |
|------|----------|
| PM Chat UI | `src/app/pm/chat/` |
| Meeting UI | `src/app/meeting/` |
| API Routes | `src/app/api/` |
| Shared Components | `src/components/` |

### Create New Meeting Component
```tsx
'use client';

import { useState, useEffect } from 'react';

interface Props {
  meetingId: string;
}

export default function MyComponent({ meetingId }: Props) {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`/api/meetings/${meetingId}`)
      .then(res => res.json())
      .then(setData);
  }, [meetingId]);

  return <div>{/* UI */}</div>;
}
```

### Create API Route
```typescript
// src/app/api/meetings/my-endpoint/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  return NextResponse.json({ data: "value" });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  return NextResponse.json({ success: true });
}
```

## Styling Pattern
Use Tailwind classes inline:
```tsx
<div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
  <h2 className="text-white font-bold">Title</h2>
</div>
```

## Don't Forget
- Use 'use client' for interactive components
- API routes are in `src/app/api/`
- Meeting components are in `src/app/meeting/components/`
- Dark theme: bg-slate-800, text-white, border-slate-700

## Related Modules
- `meeting_agent/` - Backend processing
- `mcp_meeting_server/` - MCP API
- `backend/` - PM API
