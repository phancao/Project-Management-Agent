// Copyright (c) 2025 Galaxy Technology Service
// BugBase Report Button - Floating bug icon for bug reporting

"use client";

import { useState, useCallback, useEffect } from "react";
import { Bug, X, GripVertical } from "lucide-react";
import { cn } from "~/lib/utils";
import { captureScreenshot, type ScreenshotResult } from "~/core/bugbase/screenshot-service";
import { useNavigationTracker } from "~/core/bugbase/navigation-tracker";
import { ReportForm } from "./report-form";
import { useCardGlow } from "~/core/hooks/use-theme-colors";

const POSITION_STORAGE_KEY = "bugbase-button-position";

interface Position {
    x: number;
    y: number;
}

export function ReportButton() {
    const [isOpen, setIsOpen] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
    const [position, setPosition] = useState<Position>({ x: 20, y: 20 }); // Offset from bottom-right
    const [screenshot, setScreenshot] = useState<ScreenshotResult | null>(null);
    const [isCapturing, setIsCapturing] = useState(false);
    const navigationHistory = useNavigationTracker((state) => state.entries);
    const cardGlow = useCardGlow();

    // Load saved position
    useEffect(() => {
        const saved = localStorage.getItem(POSITION_STORAGE_KEY);
        if (saved) {
            try {
                setPosition(JSON.parse(saved));
            } catch {
                // Invalid saved position, use default
            }
        }
    }, []);

    // Save position on change
    useEffect(() => {
        if (!isDragging) {
            localStorage.setItem(POSITION_STORAGE_KEY, JSON.stringify(position));
        }
    }, [position, isDragging]);

    const handleClick = useCallback(async () => {
        if (isDragging) return;

        setIsCapturing(true);
        try {
            const result = await captureScreenshot();
            setScreenshot(result);
            setIsOpen(true);
        } catch (error) {
            console.error("[BugBase] Failed to capture screenshot:", error);
            // Open form anyway without screenshot
            setIsOpen(true);
        } finally {
            setIsCapturing(false);
        }
    }, [isDragging]);

    const handleClose = useCallback(() => {
        setIsOpen(false);
        setScreenshot(null);
    }, []);

    const handleDragStart = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsDragging(true);

        const startX = e.clientX;
        const startY = e.clientY;
        const startPos = { ...position };

        const handleMouseMove = (moveEvent: MouseEvent) => {
            const deltaX = startX - moveEvent.clientX;
            const deltaY = startY - moveEvent.clientY;

            setPosition({
                x: Math.max(0, Math.min(window.innerWidth - 60, startPos.x + deltaX)),
                y: Math.max(0, Math.min(window.innerHeight - 60, startPos.y + deltaY)),
            });
        };

        const handleMouseUp = () => {
            setIsDragging(false);
            document.removeEventListener("mousemove", handleMouseMove);
            document.removeEventListener("mouseup", handleMouseUp);
        };

        document.addEventListener("mousemove", handleMouseMove);
        document.addEventListener("mouseup", handleMouseUp);
    }, [position]);

    return (
        <>
            {/* Floating Report Button */}
            <div
                data-bugbase-ignore
                className={cn(
                    "fixed z-[9999] flex items-center gap-1 transition-all duration-200",
                    isDragging && "cursor-grabbing",
                    isCapturing && "animate-pulse"
                )}
                style={{
                    right: `${position.x}px`,
                    bottom: `${position.y}px`,
                }}
            >
                {/* Drag Handle */}
                <div
                    className="p-1 rounded-l-lg bg-background/80 backdrop-blur-sm border border-r-0 border-border/50 cursor-grab hover:bg-muted/50 transition-colors"
                    onMouseDown={handleDragStart}
                >
                    <GripVertical className="w-3 h-3 text-muted-foreground" />
                </div>

                {/* Bug Button */}
                <button
                    onClick={handleClick}
                    disabled={isCapturing}
                    className={cn(
                        "p-3 rounded-r-lg bg-background/90 backdrop-blur-sm transition-all duration-300",
                        "hover:bg-brand/10 hover:scale-105",
                        "focus:outline-none focus:ring-2 focus:ring-brand/50",
                        cardGlow.className,
                        isCapturing && "opacity-50 cursor-wait"
                    )}
                    title="Report a bug"
                >
                    <Bug className={cn(
                        "w-5 h-5 text-brand transition-transform",
                        isCapturing && "animate-spin"
                    )} />
                </button>
            </div>

            {/* Report Form Modal */}
            {isOpen && (
                <ReportForm
                    screenshot={screenshot}
                    navigationHistory={navigationHistory}
                    onClose={handleClose}
                />
            )}
        </>
    );
}
