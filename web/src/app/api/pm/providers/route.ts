// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

// Get backend URL - handle both with and without /api suffix
function getBackendUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl) {
    // Remove /api if present
    return envUrl.replace(/\/api\/?$/, '');
  }
  return 'http://127.0.0.1:8000';
}

const BACKEND_URL = getBackendUrl();

export async function GET(request: NextRequest) {
  const url = `${BACKEND_URL}/api/pm/providers`;
  console.log('[API Proxy] Fetching providers from:', url);
  
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
    console.log('[API Proxy] Successfully fetched providers:', data.length);
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

