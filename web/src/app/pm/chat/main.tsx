// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { MessagesBlock } from "./components/messages-block";
import { PMViewsPanel } from "./components/pm-views-panel";

const STORAGE_KEY = "pm-chat-panel-width";
const DEFAULT_WIDTH = 40; // percentage
const MIN_WIDTH = 25; // percentage
const MAX_WIDTH = 70; // percentage

export default function Main() {
  const [chatWidth, setChatWidth] = useState(DEFAULT_WIDTH);
  const [isDragging, setIsDragging] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileView, setMobileView] = useState<"chat" | "board">("chat");
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

  // Load saved width from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const width = parseFloat(saved);
      if (width >= MIN_WIDTH && width <= MAX_WIDTH) {
        setChatWidth(width);
      }
    }
  }, []);

  // Save width to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, chatWidth.toString());
  }, [chatWidth]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging || !containerRef.current || isMobile) return;

      const container = containerRef.current;
      const rect = container.getBoundingClientRect();
      const newWidth = ((e.clientX - rect.left) / rect.width) * 100;

      // Clamp width between min and max
      const clampedWidth = Math.min(Math.max(newWidth, MIN_WIDTH), MAX_WIDTH);
      setChatWidth(clampedWidth);
    },
    [isDragging, isMobile]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Add/remove global mouse listeners for dragging
  useEffect(() => {
    if (isDragging && !isMobile) {
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
  }, [isDragging, isMobile, handleMouseMove, handleMouseUp]);

  return (
    <div ref={containerRef} className="flex h-full w-full pt-16 relative overflow-hidden bg-background">
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

      {/* Chat Panel - Left Side (resizable or full width on mobile) */}
      <div
        style={{
          width: isMobile ? "100%" : `${chatWidth}%`,
          contain: 'layout size style',
          maxWidth: isMobile ? "100%" : `${chatWidth}%`,
          display: isMobile && mobileView !== "chat" ? "none" : "flex"
        }}
        className="flex-shrink-0 flex-grow-0 border-r border-border/40 overflow-hidden bg-app/20"
      >
        <MessagesBlock className="h-full" />
      </div>

      {/* Resize Handle - Refined Desktop Experience */}
      {!isMobile && (
        <div
          className={`
            group w-1.5 flex-shrink-0 cursor-col-resize
            bg-transparent hover:bg-brand/10
            transition-all duration-300 relative
            ${isDragging ? "bg-brand/20 shadow-[0_0_15px_rgba(var(--brand),0.1)]" : ""}
          `}
          onMouseDown={handleMouseDown}
        >
          {/* Vertical line that appears on hover/drag */}
          <div className={`
            absolute inset-y-0 left-1/2 -translate-x-1/2 w-[1px]
            bg-border group-hover:bg-brand/40 transition-colors
            ${isDragging ? "bg-brand/60" : ""}
          `} />

          {/* Grabber Handle */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="w-1 h-1 rounded-full bg-border" />
            <div className="w-1 h-1 rounded-full bg-border" />
            <div className="w-1 h-1 rounded-full bg-border" />
          </div>
        </div>
      )}

      {/* PM Views Panel - Right Side (fills remaining space or full width on mobile) */}
      <div
        className={`flex-1 min-w-0 ${isMobile && mobileView !== "board" ? "hidden" : "block"}`}
      >
        <PMViewsPanel className="h-full" />
      </div>
    </div>
  );
}
