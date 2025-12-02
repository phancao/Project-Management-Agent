// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import { getBackendUrl } from '../../../../../utils/get-backend-url';

const BACKEND_URL = getBackendUrl();

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ project_id: string; epic_id: string }> }
) {
  const { project_id: projectId, epic_id: epicId } = await params;
  const decodedProjectId = decodeURIComponent(projectId);
  const decodedEpicId = decodeURIComponent(epicId);
  const url = `${BACKEND_URL}/api/pm/projects/${encodeURIComponent(decodedProjectId)}/epics/${encodeURIComponent(decodedEpicId)}`;
  console.log('[API Proxy] Updating epic at:', url);
  
  try {
    const body = await request.json();
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    
    const response = await fetch(url, {
      method: 'PUT',
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
    console.error('[API Proxy] Error updating epic:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { error: `Failed to update epic: ${errorMessage}` },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ project_id: string; epic_id: string }> }
) {
  const { project_id: projectId, epic_id: epicId } = await params;
  const decodedProjectId = decodeURIComponent(projectId);
  const decodedEpicId = decodeURIComponent(epicId);
  const url = `${BACKEND_URL}/api/pm/projects/${encodeURIComponent(decodedProjectId)}/epics/${encodeURIComponent(decodedEpicId)}`;
  console.log('[API Proxy] Deleting epic at:', url);
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
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

    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data);
  } catch (error) {
    console.error('[API Proxy] Error deleting epic:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { error: `Failed to delete epic: ${errorMessage}` },
      { status: 500 }
    );
  }
}

