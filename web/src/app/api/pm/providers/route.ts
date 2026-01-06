// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

// Get backend URL from environment
// - In Docker: API_URL=http://host.docker.internal:8000 (set in docker-compose.yml)
// - In local dev: defaults to localhost:8000
function getBackendUrl(): string {
  const url = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  // Remove trailing /api if present
  return url.replace(/\/api\/?$/, '');
}

const BACKEND_URL = getBackendUrl();

export async function GET(request: NextRequest) {
  const url = `${BACKEND_URL}/api/pm/providers`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text().catch(() => response.statusText);
      console.error('[API Proxy] Backend error:', response.status, errorText);
      return NextResponse.json(
        { error: `Backend returned ${response.status}: ${errorText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[API Proxy] Error fetching providers:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);

    // Check if it's a timeout or connection error
    if (errorMessage.includes('aborted') || errorMessage.includes('timeout')) {
      return NextResponse.json(
        { error: `Backend request timed out. Is the backend running at ${BACKEND_URL}?` },
        { status: 504 } // Gateway Timeout
      );
    }

    return NextResponse.json(
      { error: `Failed to fetch providers: ${errorMessage}` },
      { status: 500 }
    );
  }
}

