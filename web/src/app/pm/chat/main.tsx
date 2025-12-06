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
  const containerRef = useRef<HTMLDivElement>(null);

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
      if (!isDragging || !containerRef.current) return;

      const container = containerRef.current;
      const rect = container.getBoundingClientRect();
      const newWidth = ((e.clientX - rect.left) / rect.width) * 100;

      // Clamp width between min and max
      const clampedWidth = Math.min(Math.max(newWidth, MIN_WIDTH), MAX_WIDTH);
      setChatWidth(clampedWidth);
    },
    [isDragging]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Add/remove global mouse listeners for dragging
  useEffect(() => {
    if (isDragging) {
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
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div ref={containerRef} className="flex h-full w-full pt-12">
      {/* Chat Panel - Left Side (resizable) */}
      <div
        style={{ 
          width: `${chatWidth}%`,
          contain: 'layout size style',
          maxWidth: `${chatWidth}%`
        }}
        className="flex-shrink-0 flex-grow-0 border-r border-gray-200 dark:border-gray-700 overflow-hidden"
      >
        <MessagesBlock className="h-full" />
      </div>
      
      {/* Resize Handle */}
      <div
        className={`
          w-1 flex-shrink-0 cursor-col-resize
          bg-transparent hover:bg-blue-500/50
          transition-colors duration-150
          ${isDragging ? "bg-blue-500/50" : ""}
        `}
        onMouseDown={handleMouseDown}
      >
        <div className="h-full w-full" />
      </div>

      {/* PM Views Panel - Right Side (fills remaining space) */}
      <div className="flex-1 min-w-0">
        <PMViewsPanel className="h-full" />
      </div>
    </div>
  );
}
