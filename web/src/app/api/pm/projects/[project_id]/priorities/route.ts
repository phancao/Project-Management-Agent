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
  const decodedProjectId = decodeURIComponent(projectId);
  const url = `${BACKEND_URL}/api/pm/projects/${encodeURIComponent(decodedProjectId)}/priorities`;
  console.log('[API Proxy] Fetching priorities from:', url);
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    
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
    console.error('[API Proxy] Error fetching priorities:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    
    if (errorMessage.includes('aborted') || errorMessage.includes('timeout')) {
      return NextResponse.json(
        { error: `Backend request timed out. Is the backend running at ${BACKEND_URL}?` },
        { status: 504 }
      );
    }
    
    return NextResponse.json(
      { error: `Failed to fetch priorities: ${errorMessage}` },
      { status: 500 }
    );
  }
}

