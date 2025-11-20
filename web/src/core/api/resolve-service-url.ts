// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { env } from "~/env";

export function resolveServiceURL(path: string) {
  // Use direct backend connection (CORS is properly configured)
  // Next.js API route proxies exist as backup if browser blocking occurs
  let BASE_URL = env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/";
  if (!BASE_URL.endsWith("/")) {
    BASE_URL += "/";
  }
  return new URL(path, BASE_URL).toString();
}
