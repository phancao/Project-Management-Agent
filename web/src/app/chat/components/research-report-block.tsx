// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useMemo, useRef } from "react";

import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { Markdown } from "~/components/deer-flow/markdown";
import ReportEditor from "~/components/editor";
import { useReplay } from "~/core/replay";
import { useMessage, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

export function ResearchReportBlock({
  className,
  messageId,
  editing,
}: {
  className?: string;
  researchId: string;
  messageId: string;
  editing: boolean;
}) {
  const message = useMessage(messageId);
  const { isReplay } = useReplay();
  
  // Debug logging to track content disappearance
  useEffect(() => {
    if (messageId && message) {
      const contentLen = message.content?.length ?? 0;
      const chunksLen = message.contentChunks?.length ?? 0;
      const chunksTotalLen = message.contentChunks?.join("").length ?? 0;
      console.log(`[ResearchReportBlock] messageId=${messageId}, contentLen=${contentLen}, chunksLen=${chunksLen}, chunksTotalLen=${chunksTotalLen}, isStreaming=${message.isStreaming}, finishReason=${message.finishReason}`);
      if (contentLen === 0 && chunksTotalLen > 0) {
        console.warn(`[ResearchReportBlock] ⚠️ Content is empty but chunks have data! messageId=${messageId}`);
      }
      if (contentLen === 0 && chunksLen === 0 && !message.isStreaming && message.finishReason) {
        console.error(`[ResearchReportBlock] ❌ Content disappeared! messageId=${messageId}, finishReason=${message.finishReason}`);
      }
    }
  }, [messageId, message?.content, message?.contentChunks, message?.isStreaming, message?.finishReason]);
  
  const handleMarkdownChange = useCallback(
    (markdown: string) => {
      if (message) {
        message.content = markdown;
        useStore.setState({
          messages: new Map(useStore.getState().messages).set(
            message.id,
            message,
          ),
        });
      }
    },
    [message],
  );
  const contentRef = useRef<HTMLDivElement>(null);
  const isCompleted = message?.isStreaming === false && message?.content !== "";
  // Reconstruct content from chunks if main content is empty but chunks exist
  const displayContent = useMemo(() => {
    // DEBUG: Log useMemo entry for reporter messages
    if (messageId && message) {
      const contentLen = message.content?.length ?? 0;
      const chunksLen = message.contentChunks?.length ?? 0;
      const chunksTotalLen = message.contentChunks?.join("").length ?? 0;
      console.log(`[DEBUG-DISPLAY-ENTRY] 🚪 displayContent useMemo ENTRY: messageId=${messageId}, contentLen=${contentLen}, chunksLen=${chunksLen}, chunksTotalLen=${chunksTotalLen}`);
      console.trace(`[DEBUG-DISPLAY-ENTRY] Stack trace for displayContent useMemo entry`);
    }
    
    if (message?.content) {
      const result = message.content;
      // DEBUG: Log useMemo exit
      if (messageId && message) {
        console.log(`[DEBUG-DISPLAY-EXIT] 🚪 displayContent useMemo EXIT (from content): messageId=${messageId}, resultLen=${result.length}`);
      }
      return result;
    }
    // Fallback: reconstruct from contentChunks if content is empty
    if (message?.contentChunks && message.contentChunks.length > 0) {
      const reconstructed = message.contentChunks.join("");
      // DEBUG: Log useMemo exit
      if (messageId && message) {
        console.log(`[DEBUG-DISPLAY-EXIT] 🚪 displayContent useMemo EXIT (from chunks): messageId=${messageId}, reconstructedLen=${reconstructed.length}`);
      }
      return reconstructed;
    }
    // DEBUG: Log useMemo exit (empty)
    if (messageId && message) {
      console.log(`[DEBUG-DISPLAY-EXIT] 🚪 displayContent useMemo EXIT (empty): messageId=${messageId}, resultLen=0`);
    }
    return "";
  }, [messageId, message?.content, message?.contentChunks]);
  
  // TODO: scroll to top when completed, but it's not working
  // useEffect(() => {
  //   if (isCompleted && contentRef.current) {
  //     setTimeout(() => {
  //       contentRef
  //         .current!.closest("[data-radix-scroll-area-viewport]")
  //         ?.scrollTo({
  //           top: 0,
  //           behavior: "smooth",
  //         });
  //     }, 500);
  //   }
  // }, [isCompleted]);

  // Removed debug logging

  return (
    <div ref={contentRef} className={cn("w-full pt-4 pb-8", className)}>
      {displayContent.length === 0 && !message?.isStreaming ? (
        <div className="text-muted-foreground py-8 text-center text-sm">
          No content available. Content length: {message?.content?.length ?? 0}, Chunks: {message?.contentChunks?.length ?? 0}
        </div>
      ) : !isReplay && isCompleted && editing ? (
        <ReportEditor
          content={displayContent}
          onMarkdownChange={handleMarkdownChange}
        />
      ) : (
        <>
          {displayContent ? (
            <Markdown animated checkLinkCredibility>
              {displayContent}
            </Markdown>
          ) : (
            message?.isStreaming && <LoadingAnimation className="my-12" />
          )}
          {message?.isStreaming && displayContent && (
            <LoadingAnimation className="my-12" />
          )}
        </>
      )}
    </div>
  );
}
