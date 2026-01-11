// Copyright (c) 2025 Galaxy Technology Service
// BugBase Provider - Navigation tracking and report button wrapper

"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { ReportButton } from "./report-button";
import { trackNavigation } from "~/core/bugbase/navigation-tracker";

interface BugBaseProviderProps {
    children: React.ReactNode;
    enabled?: boolean;
}

export function BugBaseProvider({ children, enabled = true }: BugBaseProviderProps) {
    const pathname = usePathname();

    // Track navigation changes
    useEffect(() => {
        if (enabled && pathname) {
            trackNavigation(pathname);
        }
    }, [pathname, enabled]);

    return (
        <>
            {children}
            {enabled && <ReportButton />}
        </>
    );
}
