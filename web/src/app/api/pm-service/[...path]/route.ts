
import { NextRequest, NextResponse } from "next/server";

// Default to internal Docker service URL
// If running locally without Docker networking, this key should be set to http://localhost:8001 in .env
const SERVICE_URL = process.env.PM_SERVICE_URL || "http://pm-service:8001";

// Timeout for PM Service requests (300 seconds for large data operations)
const REQUEST_TIMEOUT_MS = 300000;

// Next.js Route Segment Config - extend timeout for long-running PM service requests
export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';
export const maxDuration = 300; // 300 seconds timeout

async function proxy(request: NextRequest, props: { params: Promise<{ path: string[] }> }) {
    const params = await props.params;
    const path = params.path.join("/");
    const search = request.nextUrl.search;
    const url = `${SERVICE_URL}/api/v1/${path}${search}`;

    console.log(`[PM-Service Proxy] Forwarding ${request.method} ${request.nextUrl.pathname} to ${url}`);

    // Create AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
        const headers = new Headers(request.headers);
        headers.delete("host");
        headers.delete("connection");


        const response = await fetch(url, {
            method: request.method,
            headers: headers,
            body: request.body ? request.body : undefined,
            // @ts-ignore - duplex is required for streaming bodies in some node versions/nextjs
            duplex: 'half',
            signal: controller.signal,
        });

        clearTimeout(timeoutId);

        const responseHeaders = new Headers(response.headers);
        // Ensure CORS is handled by Next.js or preserved

        return new NextResponse(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: responseHeaders
        });
    } catch (error) {
        clearTimeout(timeoutId);

        // Check if it's an abort error (timeout)
        if (error instanceof Error && error.name === 'AbortError') {

            console.error(`[PM-Service Proxy] Request timeout after ${REQUEST_TIMEOUT_MS}ms for ${url}`);
            return NextResponse.json(
                { error: "PM Service Request Timeout", details: `Request exceeded ${REQUEST_TIMEOUT_MS / 1000}s timeout` },
                { status: 504 }
            );
        }

        console.error(`[PM-Service Proxy] Error fetching ${url}:`, error);
        return NextResponse.json(
            { error: "PM Service Proxy Failed", details: String(error) },
            { status: 500 }
        );
    }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;
