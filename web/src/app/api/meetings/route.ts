import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/meetings
 * List all meetings
 */
// This would ideally come from env, but for internal docker comms:
const MCP_SERVER_URL = process.env.PM_MCP_SERVER_HTTP_URL || 'http://pm-mcp-server:8080';

export async function GET(request: NextRequest) {
    try {
        const { searchParams } = new URL(request.url);
        const projectId = searchParams.get('projectId');

        // Construct MCP server URL with params
        const mcpUrl = new URL(`${MCP_SERVER_URL}/meetings`);
        if (projectId) {
            mcpUrl.searchParams.append('projectId', projectId);
        }

        const res = await fetch(mcpUrl.toString(), {
            // propagate cache control or revalidate
            next: { revalidate: 0 }
        });

        if (!res.ok) {
            throw new Error(`MCP Server error: ${res.statusText}`);
        }

        const data = await res.json();
        const meetings = data.meetings || data.result?.meetings || [];

        return NextResponse.json({ meetings });
    } catch (error) {
        console.error('Failed to list meetings:', error);
        return NextResponse.json(
            { error: 'Failed to list meetings' },
            { status: 500 }
        );
    }
}
