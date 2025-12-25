import { NextRequest, NextResponse } from 'next/server';
import { writeFile, mkdir } from 'fs/promises';
import path from 'path';
import { v4 as uuid } from 'uuid';

const UPLOAD_DIR = process.env.MEETING_UPLOAD_DIR || './uploads'; // Mounts to /app/uploads in Docker
const MCP_SERVER_URL = process.env.PM_MCP_SERVER_HTTP_URL || 'http://pm-mcp-server:8080';

export async function POST(request: NextRequest) {
    try {
        const formData = await request.formData();
        const file = formData.get('file') as File;
        const title = formData.get('title') as string || 'Untitled Meeting';
        const participants = formData.get('participants') as string || '';
        const projectId = formData.get('projectId') as string || null;

        if (!file) {
            return NextResponse.json(
                { error: 'No file provided' },
                { status: 400 }
            );
        }

        // Generate ID / Filename
        const ext = file.name.split('.').pop() || 'mp3';
        const sanitizedParams = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
        const meetingId = `${Date.now()}-${uuid().slice(0, 8)}-${sanitizedParams}`;

        // Ensure upload directory exists
        // In local logic, this path is relative to CWD. In Docker, CWD is /app.
        // So './uploads' -> '/app/uploads' which is the shared volume.
        const uploadDir = path.join(process.cwd(), 'uploads');
        await mkdir(uploadDir, { recursive: true });

        // Save file
        const filePath = path.join(uploadDir, meetingId);
        const bytes = await file.arrayBuffer();
        await writeFile(filePath, Buffer.from(bytes));

        // Call MCP Tool: upload_meeting (metadata only)
        // We tell it the internal path inside the container: /app/uploads/<filename>
        const internalPath = `/app/uploads/${meetingId}`;

        const response = await fetch(`${MCP_SERVER_URL}/tools/call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: 'upload_meeting',
                arguments: {
                    file_path: internalPath,
                    filename: file.name,
                    title: title,
                    participants: participants.split(',').map(p => p.trim()).filter(Boolean),
                    project_id: projectId
                }
            })
        });

        let mcpMeetingId = null;
        if (!response.ok) {
            console.error("MCP upload registration failed", await response.text());
        } else {
            const toolRes = await response.json();
            // toolRes is expected to be [{"type": "text", "text": "JSON_STRING"}]
            if (Array.isArray(toolRes) && toolRes.length > 0 && toolRes[0].text) {
                try {
                    const data = JSON.parse(toolRes[0].text);
                    if (data.meeting_id) {
                        mcpMeetingId = data.meeting_id;
                    }
                } catch (e) {
                    console.warn("Failed to parse MCP response as JSON:", toolRes[0].text);
                }
            }
        }

        return NextResponse.json({
            meetingId: mcpMeetingId || meetingId, // Prefer MCP ID, fallback to filename
            title: title,
            message: 'File uploaded successfully',
            projectId
        });
    } catch (error) {
        console.error('Upload failed:', error);
        return NextResponse.json(
            { error: 'Upload failed' },
            { status: 500 }
        );
    }
}

export const config = {
    api: {
        bodyParser: false,
    },
};
