import { NextRequest, NextResponse } from 'next/server';

const MCP_MEETING_SERVER_URL = process.env.MCP_MEETING_SERVER_URL || 'http://localhost:8082';

/**
 * POST /api/meetings/process
 * Process an uploaded meeting (transcribe, analyze, extract)
 */
const MCP_SERVER_URL = process.env.PM_MCP_SERVER_HTTP_URL || 'http://pm-mcp-server:8080';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { meetingId, projectId } = body;

        if (!meetingId) {
            return NextResponse.json(
                { error: 'meetingId is required' },
                { status: 400 }
            );
        }

        // Call MCP Tool: process_meeting
        // We assume meetingId here corresponds to the file path or ID returned by upload
        // In our current mock upload, meetingId is just a UUID, but we need the path.
        // HOWEVER, the prev step (mock) didn't return the full path to the client.
        // Let's assume for now the client passes what it got.

        // Actually, looking at the Upload route below, we need to fix it to return the path or use the ID to lookup.
        // Or we pass the filename as meetingId?
        // Let's rely on the Upload route edit to ensure meetingId helps us find the file.
        // The Upload route (to be edited) will save to /app/uploads/filename.

        const response = await fetch(`${MCP_SERVER_URL}/tools/call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: 'process_meeting',
                arguments: {
                    meeting_id: meetingId,
                    project_id: projectId
                }
            })
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`MCP Tool call failed: ${response.status} ${errText}`);
        }

        const toolResponse = await response.json();

        // Parse the nested JSON from the MCP tool text response
        let result = null;
        if (Array.isArray(toolResponse) && toolResponse.length > 0 && toolResponse[0].text) {
            try {
                result = JSON.parse(toolResponse[0].text);
            } catch (e) {
                console.error("Failed to parse tool response:", toolResponse[0].text);
                throw new Error("Invalid response from meeting processor");
            }
        } else {
            throw new Error("Empty response from meeting processor");
        }

        if (!result.success) {
            throw new Error(result.error || 'Unknown error processing meeting');
        }

        // Return the result from the tool
        return NextResponse.json(result);
    } catch (error: any) {
        console.error('Processing failed:', error);
        return NextResponse.json(
            { error: error.message || 'Processing failed' },
            { status: 500 }
        );
    }
}
