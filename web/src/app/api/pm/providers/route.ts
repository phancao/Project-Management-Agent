// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

// Server-side: Use Docker internal URL (api is the docker-compose service name)
// API_URL env is set in docker-compose.yml for the frontend container
const BACKEND_URL = process.env.API_URL || 'http://api:8000';

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

