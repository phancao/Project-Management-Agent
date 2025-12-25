import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams;
    const projectId = searchParams.get('projectId');

    // Construct URL for MCP server
    let url = 'http://pm-mcp-server:8080/users';
    const params = new URLSearchParams();
    if (projectId) params.append('projectId', projectId);

    if (params.toString()) {
        url += `?${params.toString()}`;
    }

    try {
        const res = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
            },
            cache: 'no-store'
        });

        if (!res.ok) {
            return NextResponse.json(
                { error: `Backend Error: ${res.statusText}` },
                { status: res.status }
            );
        }

        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Error fetching users:', error);
        return NextResponse.json(
            { error: 'Internal Server Error' },
            { status: 500 }
        );
    }
}
