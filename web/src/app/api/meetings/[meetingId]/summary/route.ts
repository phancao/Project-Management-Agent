import { NextRequest, NextResponse } from 'next/server';

interface RouteParams {
    params: Promise<{ meetingId: string }>;
}

/**
 * GET /api/meetings/[meetingId]/summary
 * Get meeting summary
 */
export async function GET(
    request: NextRequest,
    props: RouteParams
) {
    const params = await props.params;
    const { meetingId } = params;

    try {
        // In production, fetch from MCP Meeting Server
        // For demo, return placeholder data
        const summary = {
            meetingId,
            title: 'Weekly Standup Meeting',
            executiveSummary: 'The team discussed sprint progress, identified blockers, and aligned on priorities for the coming week. Key decisions were made regarding the API integration timeline.',
            keyPoints: [
                'Sprint velocity is on track at 85% completion',
                'API integration blocked by external dependency',
                'New feature requirements added to backlog',
                'Team capacity reduced next week due to holidays',
                'QA testing phase starting Monday',
            ],
            topics: [
                'Sprint Progress',
                'API Integration',
                'Resource Planning',
                'Testing Strategy',
            ],
            participantContributions: {
                'Alice': ['Led sprint review discussion', 'Proposed timeline adjustment'],
                'Bob': ['Reported API integration status', 'Identified dependency blocker'],
                'Charlie': ['Presented QA testing plan', 'Requested additional test coverage'],
            },
            sentiment: 'positive',
            actionItemsCount: 5,
            decisionsCount: 2,
            followUpsCount: 3,
        };

        return NextResponse.json(summary);
    } catch (error) {
        console.error('Failed to get summary:', error);
        return NextResponse.json(
            { error: 'Failed to get summary' },
            { status: 500 }
        );
    }
}
