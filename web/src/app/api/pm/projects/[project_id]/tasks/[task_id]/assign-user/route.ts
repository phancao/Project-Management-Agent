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

export async function POST(
  request: NextRequest,
  { params }: { params: { project_id: string; task_id: string } }
) {
  const projectId = params.project_id;
  const taskId = params.task_id;
  const decodedProjectId = decodeURIComponent(projectId);
  const decodedTaskId = decodeURIComponent(taskId);
  const url = `${BACKEND_URL}/api/pm/projects/${encodeURIComponent(decodedProjectId)}/tasks/${encodeURIComponent(decodedTaskId)}/assign-user`;
  console.log('[API Proxy] Assigning user to task at:', url);
  
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
    console.error('[API Proxy] Error assigning user to task:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { error: `Failed to assign user: ${errorMessage}` },
      { status: 500 }
    );
  }
}

