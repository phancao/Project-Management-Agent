import { NextRequest, NextResponse } from 'next/server';

const MCP_MEETING_SERVER_URL = process.env.MCP_MEETING_SERVER_URL || 'http://localhost:8082';

/**
 * POST /api/meetings/process
 * Process an uploaded meeting (transcribe, analyze, extract)
 */
export async function POST(request: NextRequest) {
    try {
        const { meetingId, language } = await request.json();

        if (!meetingId) {
            return NextResponse.json(
                { error: 'meetingId is required' },
                { status: 400 }
            );
        }

        // Call MCP Meeting Server to process
        // In production, this would be an actual call to the MCP server
        // For now, simulate the response

        // Simulated delay for processing
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Simulated response
        const result = {
            meetingId,
            status: 'completed',
            summary: {
                executiveSummary: 'This was a productive meeting discussing Q1 goals and action items.',
                keyPoints: [
                    'Reviewed Q1 objectives and KPIs',
                    'Discussed resource allocation',
                    'Agreed on timeline for deliverables',
                ],
                actionItemsCount: 5,
                decisionsCount: 2,
            },
        };

        // In production:
        // const response = await fetch(`${MCP_MEETING_SERVER_URL}/tools/call`, {
        //   method: 'POST',
        //   headers: { 'Content-Type': 'application/json' },
        //   body: JSON.stringify({
        //     name: 'process_meeting',
        //     arguments: { meeting_id: meetingId, language },
        //   }),
        // });

        return NextResponse.json(result);
    } catch (error) {
        console.error('Processing failed:', error);
        return NextResponse.json(
            { error: 'Processing failed' },
            { status: 500 }
        );
    }
}
