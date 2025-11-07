const STORAGE_KEY = "pm:sprintboard:trace";

let traceEnabled = false;

const readInitialSetting = () => {
  if (typeof window === "undefined") {
    return process.env.NODE_ENV === "development";
  }

  try {
    const storedValue = window.localStorage.getItem(STORAGE_KEY);
    if (storedValue === null) {
      const defaultValue = process.env.NODE_ENV === "development";
      if (defaultValue) window.localStorage.setItem(STORAGE_KEY, "true");
      return defaultValue;
    }
    return storedValue === "true";
  } catch {
    return process.env.NODE_ENV === "development";
  }
};

const persistSetting = (value: boolean) => {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, value ? "true" : "false");
  } catch {
    // ignore persistence issues
  }
};

traceEnabled = readInitialSetting();

export const setSprintBoardTraceEnabled = (value: boolean) => {
  traceEnabled = value;
  persistSetting(value);
};

export const isSprintBoardTraceEnabled = () => traceEnabled;

export const traceSprintBoardEvent = (event: string, payload: Record<string, unknown>) => {
  if (!traceEnabled) return;

  const timestamp = new Date().toISOString();
  const label = `[SprintBoardTrace][${timestamp}] ${event}`;

  if (typeof console.groupCollapsed === "function") {
    console.groupCollapsed(label);
    console.log(payload);
    console.groupEnd();
    return;
  }

  console.log(label, payload);
};

if (typeof window !== "undefined") {
  (window as typeof window & {
    __sprintBoardTrace?: {
      enable: () => void;
      disable: () => void;
      status: () => boolean;
    };
  }).__sprintBoardTrace = {
    enable: () => setSprintBoardTraceEnabled(true),
    disable: () => setSprintBoardTraceEnabled(false),
    status: () => isSprintBoardTraceEnabled(),
  };
}
