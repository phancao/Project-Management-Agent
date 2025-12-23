import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/meetings
 * List all meetings
 */
export async function GET(request: NextRequest) {
    try {
        const { searchParams } = new URL(request.url);
        const projectId = searchParams.get('projectId');

        // In production, fetch from MCP Meeting Server
        // For now, return demo data
        const allMeetings = [
            {
                id: 'mtg_demo001',
                title: 'Weekly Standup',
                status: 'completed',
                createdAt: new Date().toISOString(),
                participantsCount: 5,
                actionItemsCount: 3,
                projectId: 'mock-proj-1',
            },
            {
                id: 'mtg_demo002',
                title: 'Project Planning',
                status: 'pending',
                createdAt: new Date(Date.now() - 86400000).toISOString(),
                participantsCount: 3,
                projectId: 'mock-proj-1',
            },
            {
                id: 'mtg_demo003',
                title: 'Marketing Sync',
                status: 'completed',
                createdAt: new Date(Date.now() - 172800000).toISOString(),
                participantsCount: 4,
                projectId: 'mock-proj-2',
            }
        ];

        // Filter by projectId if provided, otherwise return all
        // In a real app, you might want to only show meetings unrelated to any project if no project is selected
        const meetings = projectId
            ? allMeetings.filter(m => m.projectId === projectId || !m.projectId)
            : allMeetings;

        return NextResponse.json({ meetings });
    } catch (error) {
        console.error('Failed to list meetings:', error);
        return NextResponse.json(
            { error: 'Failed to list meetings' },
            { status: 500 }
        );
    }
}
