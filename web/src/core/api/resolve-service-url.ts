// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { env } from "~/env";

export function resolveServiceURL(path: string) {
  // Use direct backend connection (CORS is properly configured)
  // Next.js API route proxies exist as backup if browser blocking occurs
  let baseUrl = env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/";

  // Remove trailing slash if present
  if (baseUrl.endsWith('/')) {
    baseUrl = baseUrl.slice(0, -1);
  }

  // Append /api if not present
  if (!baseUrl.endsWith('/api')) {
    baseUrl += '/api';
  }

  // Ensure trailing slash for URL constructor
  baseUrl += '/';

  return new URL(path, baseUrl).toString();
}
