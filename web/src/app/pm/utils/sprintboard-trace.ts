/*
 * Sprint board tracing is fully disabled. The module keeps the same API
 * surface so existing imports continue to work, but every function is a no-op.
 */

export const setSprintBoardTraceEnabled = (_value: boolean) => {
  // no-op
};

export const isSprintBoardTraceEnabled = () => false;

export const traceSprintBoardEvent = (_event: string, _payload: Record<string, unknown>) => {
  // no-op
};

declare global {
  interface Window {
    __sprintBoardTrace?: {
      enable: () => void;
      disable: () => void;
      status: () => boolean;
    };
  }
}

if (typeof window !== "undefined") {
  window.__sprintBoardTrace = {
    enable: () => {
      /* no-op */
    },
    disable: () => {
      /* no-op */
    },
    status: () => false,
  };
}
