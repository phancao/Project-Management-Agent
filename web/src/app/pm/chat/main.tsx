// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, MessageSquare } from "lucide-react";
import { MessagesBlock } from "./components/messages-block";
import { PMViewsPanel } from "./components/pm-views-panel";

const STORAGE_KEY = "pm-chat-panel-width";
const COLLAPSE_STORAGE_KEY = "pm-chat-panel-collapsed";
const DEFAULT_WIDTH = 40; // percentage
const MIN_WIDTH = 25; // percentage
const MAX_WIDTH = 70; // percentage

export default function Main() {
  const [chatWidth, setChatWidth] = useState(DEFAULT_WIDTH);
  const [isDragging, setIsDragging] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileView, setMobileView] = useState<"chat" | "board">("chat");
  const [isCollapsed, setIsCollapsed] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Detect mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024); // Use 1024 for tablet/mobile range
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Load saved width and collapse state from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const width = parseFloat(saved);
      if (width >= MIN_WIDTH && width <= MAX_WIDTH) {
        setChatWidth(width);
      }
    }

    const savedCollapsed = localStorage.getItem(COLLAPSE_STORAGE_KEY);
    if (savedCollapsed) {
      setIsCollapsed(savedCollapsed === "true");
    }
  }, []);

  // Save width to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, chatWidth.toString());
  }, [chatWidth]);

  // Save collapse state to localStorage
  useEffect(() => {
    localStorage.setItem(COLLAPSE_STORAGE_KEY, isCollapsed.toString());
  }, [isCollapsed]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging || !containerRef.current || isMobile || isCollapsed) return;

      const container = containerRef.current;
      const rect = container.getBoundingClientRect();
      const newWidth = ((e.clientX - rect.left) / rect.width) * 100;

      // Clamp width between min and max
      const clampedWidth = Math.min(Math.max(newWidth, MIN_WIDTH), MAX_WIDTH);
      setChatWidth(clampedWidth);
    },
    [isDragging, isMobile, isCollapsed]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const toggleCollapse = useCallback(() => {
    setIsCollapsed((prev) => !prev);
  }, []);

  // Add/remove global mouse listeners for dragging
  useEffect(() => {
    if (isDragging && !isMobile && !isCollapsed) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isDragging, isMobile, isCollapsed, handleMouseMove, handleMouseUp]);

  return (
    <div ref={containerRef} className={`flex h-full w-full relative overflow-hidden bg-background ${isMobile ? "pt-16" : "pt-0"}`}>
      {/* Mobile Toggle */}
      {isMobile && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-40 bg-white/95 dark:bg-gray-800/95 backdrop-blur-md shadow-lg border border-gray-200/50 dark:border-gray-700/50 rounded-full p-1.5 flex gap-1">
          <button
            onClick={() => setMobileView("chat")}
            className={`px-6 py-2 rounded-full text-xs font-bold whitespace-nowrap transition-all duration-300 ${mobileView === "chat"
              ? "bg-blue-600 text-white shadow-md scale-105"
              : "text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
          >
            AI Chat
          </button>
          <button
            onClick={() => setMobileView("board")}
            className={`px-6 py-2 rounded-full text-xs font-bold whitespace-nowrap transition-all duration-300 ${mobileView === "board"
              ? "bg-blue-600 text-white shadow-md scale-105"
              : "text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
          >
            Management
          </button>
        </div>
      )}

      {/* Collapsed State - Expand Button */}
      {!isMobile && isCollapsed && (
        <div className="flex-shrink-0 w-12 h-full bg-background border-r border-border/40 flex flex-col items-center py-4 gap-2">
          <button
            onClick={toggleCollapse}
            className="p-2 rounded-lg bg-brand/10 hover:bg-brand/20 text-brand transition-all duration-200 group"
            title="Expand chat panel"
          >
            <ChevronRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
          </button>
          <div className="flex-1 flex items-center justify-center">
            <div className="writing-mode-vertical text-xs text-muted-foreground font-medium flex items-center gap-2 rotate-180" style={{ writingMode: 'vertical-rl' }}>
              <MessageSquare className="w-4 h-4 rotate-90" />
              AI Chat
            </div>
          </div>
        </div>
      )}

      {/* Chat Panel - Left Side (resizable or full width on mobile) */}
      {(!isCollapsed || isMobile) && (
        <div
          style={{
            width: isMobile ? "100%" : `${chatWidth}%`,
            contain: 'layout size style',
            maxWidth: isMobile ? "100%" : `${chatWidth}%`,
            display: isMobile && mobileView !== "chat" ? "none" : "flex"
          }}
          className="flex-shrink-0 flex-grow-0 border-r border-border/40 overflow-hidden bg-transparent transition-all duration-300"
        >
          <MessagesBlock className="h-full" />
        </div>
      )}

      {/* Resize Handle with Collapse Button - Refined Desktop Experience */}
      {!isMobile && !isCollapsed && (
        <div
          className={`
            group w-4 flex-shrink-0 cursor-col-resize
            bg-transparent hover:bg-brand/5
            transition-all duration-300 relative
            ${isDragging ? "bg-brand/10" : ""}
          `}
          onMouseDown={handleMouseDown}
        >
          {/* Vertical line that appears on hover/drag */}
          <div className={`
            absolute inset-y-0 left-1/2 -translate-x-1/2 w-[1px]
            bg-border group-hover:bg-brand/40 transition-colors
            ${isDragging ? "bg-brand/60" : ""}
          `} />

          {/* Collapse Button - centered on handle */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleCollapse();
            }}
            onMouseDown={(e) => e.stopPropagation()}
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 
              p-1.5 rounded-full bg-background border border-border shadow-sm
              hover:bg-brand/10 hover:border-brand/30 hover:shadow-md
              transition-all duration-200 opacity-0 group-hover:opacity-100 z-10"
            title="Collapse chat panel"
          >
            <ChevronLeft className="w-3.5 h-3.5 text-muted-foreground hover:text-brand" />
          </button>

          {/* Grabber dots */}
          <div className="absolute top-[calc(50%-30px)] left-1/2 -translate-x-1/2 flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="w-1 h-1 rounded-full bg-border" />
            <div className="w-1 h-1 rounded-full bg-border" />
            <div className="w-1 h-1 rounded-full bg-border" />
          </div>
          <div className="absolute top-[calc(50%+20px)] left-1/2 -translate-x-1/2 flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="w-1 h-1 rounded-full bg-border" />
            <div className="w-1 h-1 rounded-full bg-border" />
            <div className="w-1 h-1 rounded-full bg-border" />
          </div>
        </div>
      )}

      {/* PM Views Panel - Right Side (fills remaining space or full width on mobile) */}
      <div
        className={`flex-1 min-w-0 transition-all duration-300 ${isMobile && mobileView !== "board" ? "hidden" : "block"}`}
      >
        <PMViewsPanel className="h-full" />
      </div>
    </div>
  );
}

