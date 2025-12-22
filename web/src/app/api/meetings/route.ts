import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/meetings
 * List all meetings
 */
export async function GET(request: NextRequest) {
    try {
        // In production, fetch from MCP Meeting Server
        // For now, return demo data
        const meetings = [
            {
                id: 'mtg_demo001',
                title: 'Weekly Standup',
                status: 'completed',
                createdAt: new Date().toISOString(),
                participantsCount: 5,
                actionItemsCount: 3,
            },
            {
                id: 'mtg_demo002',
                title: 'Project Planning',
                status: 'pending',
                createdAt: new Date(Date.now() - 86400000).toISOString(),
                participantsCount: 3,
            },
        ];

        return NextResponse.json({ meetings });
    } catch (error) {
        console.error('Failed to list meetings:', error);
        return NextResponse.json(
            { error: 'Failed to list meetings' },
            { status: 500 }
        );
    }
}
