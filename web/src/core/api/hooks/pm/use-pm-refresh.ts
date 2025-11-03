// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useRef } from "react";

/**
 * Hook to listen for PM refresh events from chat stream
 * Triggers a callback when PM data should be refreshed
 */
export function usePMRefresh(onRefresh: () => void) {
  const callbackRef = useRef(onRefresh);
  
  useEffect(() => {
    callbackRef.current = onRefresh;
  }, [onRefresh]);

  useEffect(() => {
    const handleRefresh = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (customEvent.detail?.type === "pm_refresh") {
        callbackRef.current();
      }
    };

    window.addEventListener("pm_refresh", handleRefresh);
    
    return () => {
      window.removeEventListener("pm_refresh", handleRefresh);
    };
  }, []);
}

/**
 * Dispatch PM refresh event
 * Call this after receiving pm_refresh event from SSE stream
 */
export function dispatchPMRefresh() {
  window.dispatchEvent(new CustomEvent("pm_refresh", { 
    detail: { type: "pm_refresh" } 
  }));
}

