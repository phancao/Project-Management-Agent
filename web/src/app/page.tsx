// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { redirect } from 'next/navigation';

// This page handles two cases:
// 1. Normal visit -> redirect to /pm/chat
// 2. OAuth callback from Azure AD -> forward to backend with code & state

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ code?: string; state?: string; error?: string; error_description?: string }>;
}) {
  // Await searchParams (Next.js 15 requires this)
  const params = await searchParams;

  // Check if this is an OAuth callback (has code and state params)
  if (params.code && params.state) {
    // Forward to backend to complete OAuth flow
    const backendUrl = `/api/auth/azure/callback?code=${encodeURIComponent(params.code)}&state=${encodeURIComponent(params.state)}`;
    redirect(backendUrl);
  }

  // Check for OAuth errors
  if (params.error) {
    const errorUrl = `/login?error=${encodeURIComponent(params.error)}&error_description=${encodeURIComponent(params.error_description || '')}`;
    redirect(errorUrl);
  }

  // Normal case - redirect to main app
  redirect('/pm/chat');
}
