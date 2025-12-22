import { NextRequest, NextResponse } from 'next/server';

interface RouteParams {
    params: { meetingId: string };
}

/**
 * GET /api/meetings/[meetingId]/action-items
 * Get action items for a meeting
 */
export async function GET(
    request: NextRequest,
    { params }: RouteParams
) {
    const { meetingId } = params;

    try {
        // In production, fetch from MCP Meeting Server
        // For demo, return placeholder data
        const actionItems = [
            {
                id: 'ai_001',
                description: 'Complete API documentation for external integration',
                assigneeName: 'Bob',
                dueDate: '2024-01-15',
                dueDateText: 'by end of next week',
                priority: 'high',
                status: 'pending',
                sourceQuote: 'Bob said he would have the API docs ready by next Friday',
                pmTaskId: null,
            },
            {
                id: 'ai_002',
                description: 'Set up test environment for QA team',
                assigneeName: 'Charlie',
                dueDate: '2024-01-12',
                dueDateText: 'before Monday',
                priority: 'critical',
                status: 'pending',
                sourceQuote: 'We need the test environment ready before QA starts on Monday',
                pmTaskId: null,
            },
            {
                id: 'ai_003',
                description: 'Schedule follow-up meeting with stakeholders',
                assigneeName: 'Alice',
                dueDate: null,
                dueDateText: 'this week',
                priority: 'medium',
                status: 'pending',
                sourceQuote: 'Alice will set up a meeting with stakeholders to discuss timeline',
                pmTaskId: null,
            },
            {
                id: 'ai_004',
                description: 'Review and update sprint backlog priorities',
                assigneeName: null,
                dueDate: null,
                dueDateText: null,
                priority: 'low',
                status: 'pending',
                sourceQuote: 'Someone needs to review the backlog and reprioritize',
                pmTaskId: null,
            },
            {
                id: 'ai_005',
                description: 'Investigate external API rate limiting issue',
                assigneeName: 'Bob',
                dueDate: '2024-01-10',
                dueDateText: 'ASAP',
                priority: 'high',
                status: 'in_progress',
                sourceQuote: 'Bob is already looking into the rate limiting problem',
                pmTaskId: 'task_12345',
            },
        ];

        return NextResponse.json({ actionItems });
    } catch (error) {
        console.error('Failed to get action items:', error);
        return NextResponse.json(
            { error: 'Failed to get action items' },
            { status: 500 }
        );
    }
}
