// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getBackendUrl } from '../../../../utils/get-backend-url';

const BACKEND_URL = getBackendUrl();

export async function GET(
  request: NextRequest,
  { params }: { params: { project_id: string } }
) {
  const projectId = params.project_id;
  // URL decode the project_id in case it's encoded
  const decodedProjectId = decodeURIComponent(projectId);
  const url = `${BACKEND_URL}/api/pm/projects/${encodeURIComponent(decodedProjectId)}/tasks`;
  console.log('[API Proxy] Fetching tasks from:', url);
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
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
    console.log('[API Proxy] Successfully fetched tasks:', data.length);
    return NextResponse.json(data);
  } catch (error) {
    console.error('[API Proxy] Error fetching tasks:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    
    // Check if it's a timeout or connection error
    if (errorMessage.includes('aborted') || errorMessage.includes('timeout')) {
      return NextResponse.json(
        { error: `Backend request timed out. Is the backend running at ${BACKEND_URL}?` },
        { status: 504 } // Gateway Timeout
      );
    }
    
    return NextResponse.json(
      { error: `Failed to fetch tasks: ${errorMessage}` },
      { status: 500 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { project_id: string } }
) {
  const projectId = params.project_id;
  const decodedProjectId = decodeURIComponent(projectId);
  const url = `${BACKEND_URL}/api/pm/projects/${encodeURIComponent(decodedProjectId)}/tasks`;
  console.log('[API Proxy] Creating task at:', url);
  
  try {
    const body = await request.json();
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text().catch(() => response.statusText);
      return NextResponse.json(
        { error: `Backend returned ${response.status}: ${errorText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[API Proxy] Error creating task:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { error: `Failed to create task: ${errorMessage}` },
      { status: 500 }
    );
  }
}

