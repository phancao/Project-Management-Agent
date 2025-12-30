"use client";

// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { LoadingOutlined } from "@ant-design/icons";
import { motion } from "framer-motion";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  Download,
  Headphones,
  ChevronDown,
  ChevronRight,
  Lightbulb,
  Wrench,
} from "lucide-react";
import { useTranslations } from "next-intl";
import React, { useCallback, useMemo, useRef, useState } from "react";

import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { Markdown } from "~/components/deer-flow/markdown";
import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { RollingText } from "~/components/deer-flow/rolling-text";
import {
  ScrollContainer,
  type ScrollContainerRef,
} from "~/components/deer-flow/scroll-container";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "~/components/ui/collapsible";
import type { Message, Option } from "~/core/messages";
import {
  closeResearch,
  openResearch,
  useLastFeedbackMessageId,
  useLastInterruptMessage,
  useMessage,
  useRenderableMessageIds,
  useResearchMessage,
  useStore,
} from "~/core/store";
import { parseJSON } from "~/core/utils";
import { cn } from "~/lib/utils";



export function MessageListView({
  className,
  onFeedback,
  onSendMessage,
}: {
  className?: string;
  onFeedback?: (feedback: { option: Option }) => void;
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
}) {
  const scrollContainerRef = useRef<ScrollContainerRef>(null);
  // Use renderable message IDs to avoid React key warnings from duplicate or non-rendering messages
  const messageIds = useStore((state) => state.messageIds);
  const messages = useStore((state) => state.messages);
  const interruptMessage = useLastInterruptMessage();
  const waitingForFeedbackMessageId = useLastFeedbackMessageId();
  const responding = useStore((state) => state.responding);
  const noOngoingResearch = useStore(
    (state) => state.ongoingResearchId === null,
  );
  const ongoingResearchIsOpen = useStore(
    (state) => state.ongoingResearchId === state.openResearchId,
  );

  // FIX: Always show loading when responding=true
  // The old logic hid loading when ongoingResearchId === openResearchId, assuming a research
  // side-panel was visible. But PM queries don't have a visible research panel, leaving users
  // with no feedback during the ~36 second "dead zone" while waiting for the report.
  const showLoading = responding;

  const handleToggleResearch = useCallback(() => {
    // Fix the issue where auto-scrolling to the bottom
    // occasionally fails when toggling research.
    const timer = setTimeout(() => {
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollToBottom();
      }
    }, 500);
    return () => {
      clearTimeout(timer);
    };
  }, []);

  return (
    <ScrollContainer
      className={cn("flex h-full w-full flex-col overflow-hidden", className)}
      scrollShadowColor="var(--app-background)"
      autoScrollToBottom
      ref={scrollContainerRef}
    >
      <ul className="flex flex-col">
        {messageIds.map((messageId, index) => (
          <MessageListItem
            key={messageId}
            messageId={messageId}
            isLast={index === messageIds.length - 1}
            waitForFeedback={waitingForFeedbackMessageId === messageId}
            interruptMessage={interruptMessage}
            onFeedback={onFeedback}
            onSendMessage={onSendMessage}
            onToggleResearch={handleToggleResearch}
          />
        ))}
        <div className="flex h-8 w-full shrink-0"></div>
      </ul>
      {showLoading && (
        <LoadingAnimation className="w-full" />
      )}
    </ScrollContainer>
  );
}

function MessageListItem({
  className,
  messageId,
  isLast,
  waitForFeedback,
  interruptMessage,
  onFeedback,
  onSendMessage,
  onToggleResearch,
}: {
  className?: string;
  messageId: string;
  isLast?: boolean;
  waitForFeedback?: boolean;
  onFeedback?: (feedback: { option: Option }) => void;
  interruptMessage?: Message | null;
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
  onToggleResearch?: () => void;
}) {
  const message = useMessage(messageId);

  const researchIds = useStore((state) => state.researchIds);
  const startOfResearch = useMemo(() => {
    // CRITICAL: Filter out undefined/null researchIds to prevent bugs
    const validResearchIds = researchIds.filter(id => id != null && id !== undefined);
    const isStart = validResearchIds.includes(messageId);

    return isStart;
  }, [researchIds, messageId]);

  // Safety check: ensure message exists before rendering
  if (!message) {
    return null;
  }

  if (message) {
    // Check if this planner message is part of a research block
    // If so, don't render it separately - it will be shown in AnalysisBlock
    const researchPlanIds = useStore((state) => state.researchPlanIds);
    const isPlannerInResearch = message.agent === "planner" &&
      researchPlanIds &&
      Array.from(researchPlanIds.values()).includes(message.id);

    // Skip rendering planner messages that are part of research blocks
    // They will be shown in AnalysisBlock instead
    if (isPlannerInResearch) {

      return null;
    }

    let content: React.ReactNode | null = null;

    if (
      message.role === "user" ||
      message.agent === "coordinator" ||
      message.agent === "react_agent" ||
      startOfResearch
      // Note: reporter is NOT included here - report is shown inside AnalysisBlock
    ) {

      // Priority 1: If this is the start of research, route to correct component based on agent
      if (startOfResearch && message?.id) {
        const state = useStore.getState();
        const isReactAgent = message.agent === "react_agent";
        const isPlanner = message.agent === "planner";
        const escalationLink = state.reactToPlannerEscalation.get(message.id);

        // Phase 4: Route based on agent type and escalation
        if (isPlanner) {
          // Planner agent: Use PlanCard (fallback)

          content = (
            <div className="w-full px-4">
              <PlanCard
                message={message}
                waitForFeedback={waitForFeedback}
                interruptMessage={interruptMessage}
                onFeedback={onFeedback}
                onSendMessage={onSendMessage}
              />
            </div>
          );
        }
      } else {
        // Fallback: Use MessageBubble for other agents

        // EXTRACT TOOLS
        const toolNames = message.toolCalls?.map((t) => t.name) || [];

        content = (
          <div className="w-full px-4">
            <MessageBubble message={message}>
              <div className="flex w-full flex-col break-words">
                <Markdown
                  className={cn(
                    message.role === "user" &&
                    "prose-invert not-dark:text-secondary dark:text-inherit",
                  )}
                >
                  {message?.content}
                </Markdown>
                {/* SHOW TOOLS AND RESULTS */}
                {message.toolCalls && message.toolCalls.length > 0 && (
                  <ToolsDisplay toolCalls={message.toolCalls} />
                )}
              </div>
            </MessageBubble>
          </div>
        );
      }
    } else if (message.agent === "planner") {

      // Show PlanCard for standalone planner messages (not in research)
      content = (
        <div className="w-full px-4">
          <PlanCard
            message={message}
            waitForFeedback={waitForFeedback}
            interruptMessage={interruptMessage}
            onFeedback={onFeedback}
            onSendMessage={onSendMessage}
          />
        </div>
      );
    } else if (message.agent === "podcast") {

      content = (
        <div className="w-full px-4">
          <PodcastCard message={message} />
        </div>
      );
    } else {

      // Render Guard: Strict checks to prevent "Ghost Bubbles" (empty 1px UI)
      // This allows the backend to stream pure whitespace (for formatting) without breaking the UI.
      const hasVisibleContent = message.content && /\S/.test(message.content); // Checks for any non-whitespace character
      const validTools = message.toolCalls?.filter(t => t.name && t.name.trim()) || [];
      const hasTools = validTools.length > 0;
      const hasThoughts = message.reactThoughts && message.reactThoughts.length > 0;

      const shouldRender = hasVisibleContent || hasTools || hasThoughts;

      // DEBUG: Log specific rejection reason if needed (commented out for prod)
      // if (!shouldRender && message.content) {
      //   console.debug(`[MessageListView] Ghost Bubble prevented: content='${message.content}'`);
      // }

      content = shouldRender ? (
        <div
          className={cn(
            "flex w-full px-4",
            className,
          )}
        >
          <MessageBubble message={message}>
            <div className="flex w-full flex-col break-words">
              {hasVisibleContent && (
                <Markdown
                  className={cn()}
                >
                  {message?.content}
                </Markdown>
              )}
              {/* SHOW THOUGHTS (Detected intent, etc) */}
              {hasThoughts && (
                <div className="flex flex-col gap-2 mb-2">
                  {message.reactThoughts?.map((thought, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/40 p-2 rounded-md border border-border/50">
                      <span>{thought.thought}</span>
                    </div>
                  ))}
                </div>
              )}
              {/* SHOW TOOLS AND RESULTS for pm_agent and other agents */}
              {hasTools && (
                <ToolsDisplay toolCalls={validTools} />
              )}
            </div>
          </MessageBubble>
        </div>
      ) : null;
    }
    if (content) {
      return (
        <motion.li
          className="mt-10"
          key={messageId}
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ transition: "all 0.2s ease-out" }}
          transition={{
            duration: 0.2,
            ease: "easeOut",
          }}
        >
          {content}
        </motion.li>
      );
    }
  }
  return null;
}


function MessageBubble({
  className,
  message,
  children,
}: {
  className?: string;
  message: Message;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "group flex w-auto max-w-[90vw] flex-col rounded-2xl px-4 py-3 break-words",
        message.role === "user" && "bg-brand rounded-ee-none",
        message.role === "assistant" && "bg-card rounded-es-none",
        className,
      )}
      style={{ wordBreak: "break-all" }}
    >
      {message.role === "assistant" && message.agent && (
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground opacity-70">
          {message.agent === "react_agent" ? "React" : message.agent.replace(/_/g, " ")}
        </div>
      )}
      {children}
    </div>
  );
}

function ResearchCard({
  className,
  researchId,
  onToggleResearch,
}: {
  className?: string;
  researchId: string;
  onToggleResearch?: () => void;
}) {
  const t = useTranslations("chat.research");
  const reportId = useStore((state) => state.researchReportIds.get(researchId));
  const hasReport = reportId !== undefined;
  const reportGenerating = useStore(
    (state) => hasReport && state.messages.get(reportId)!.isStreaming,
  );
  const openResearchId = useStore((state) => state.openResearchId);
  const state = useMemo(() => {
    if (hasReport) {
      return reportGenerating ? t("generatingReport") : t("reportGenerated");
    }
    return t("researching");
  }, [hasReport, reportGenerating, t]);
  const msg = useResearchMessage(researchId);
  const title = useMemo(() => {
    if (msg) {
      return parseJSON(msg.content ?? "", { title: "" }).title;
    }
    return undefined;
  }, [msg]);
  const handleOpen = useCallback(() => {
    if (openResearchId === researchId) {
      closeResearch();
    } else {
      openResearch(researchId);
    }
    onToggleResearch?.();
  }, [openResearchId, researchId, onToggleResearch]);
  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle>
          <RainbowText animated={state !== t("reportGenerated")}>
            {title !== undefined && title !== "" ? title : t("deepResearch")}
          </RainbowText>
        </CardTitle>
      </CardHeader>
      <CardFooter>
        <div className="flex w-full">
          <RollingText className="text-muted-foreground flex-grow text-sm">
            {state}
          </RollingText>
          <Button
            variant={!openResearchId ? "default" : "outline"}
            onClick={handleOpen}
          >
            {researchId !== openResearchId ? t("open") : t("close")}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}

function ThoughtBlock({
  className,
  content,
  isStreaming,
  hasMainContent,
  contentChunks,
}: {
  className?: string;
  content: string;
  isStreaming?: boolean;
  hasMainContent?: boolean;
  contentChunks?: string[];
}) {
  const t = useTranslations("chat.research");
  const [isOpen, setIsOpen] = useState(true);

  const [hasAutoCollapsed, setHasAutoCollapsed] = useState(false);

  React.useEffect(() => {
    if (hasMainContent && !hasAutoCollapsed) {
      setIsOpen(false);
      setHasAutoCollapsed(true);
    }
  }, [hasMainContent, hasAutoCollapsed]);

  if (!content || content.trim() === "") {
    return null;
  }

  // Split content into static (previous chunks) and streaming (current chunk)
  const chunks = contentChunks ?? [];
  const staticContent = chunks.slice(0, -1).join("");
  const streamingChunk = isStreaming && chunks.length > 0 ? (chunks[chunks.length - 1] ?? "") : "";
  const hasStreamingContent = isStreaming && streamingChunk.length > 0;

  return (
    <div className={cn("mb-6 w-full", className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className={cn(
              "h-auto w-full justify-start rounded-xl border px-6 py-4 text-left transition-all duration-200",
              "hover:bg-accent hover:text-accent-foreground",
              isStreaming
                ? "border-primary/20 bg-primary/5 shadow-sm"
                : "border-border bg-card",
            )}
          >
            <div className="flex w-full items-center gap-3">
              <Lightbulb
                size={18}
                className={cn(
                  "shrink-0 transition-colors duration-200",
                  isStreaming ? "text-primary" : "text-muted-foreground",
                )}
              />
              <span
                className={cn(
                  "leading-none font-semibold transition-colors duration-200",
                  isStreaming ? "text-primary" : "text-foreground",
                )}
              >
                {t("deepThinking")}
              </span>
              {isStreaming && <LoadingAnimation className="ml-2 scale-75" />}
              <div className="flex-grow" />
              {isOpen ? (
                <ChevronDown
                  size={16}
                  className="text-muted-foreground transition-transform duration-200"
                />
              ) : (
                <ChevronRight
                  size={16}
                  className="text-muted-foreground transition-transform duration-200"
                />
              )}
            </div>
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:slide-up-2 data-[state=open]:slide-down-2 mt-3">
          <Card
            className={cn(
              "transition-all duration-200",
              isStreaming ? "border-primary/20 bg-primary/5" : "border-border",
            )}
          >
            <CardContent>
              <div className="flex w-full">
                <ScrollContainer
                  className={cn(
                    "flex h-full w-full flex-col overflow-hidden break-words [word-break:break-word] [overflow-wrap:anywhere]",
                    className,
                  )}
                  scrollShadow={false}
                  autoScrollToBottom
                >
                  {staticContent && (
                    <Markdown
                      className={cn(
                        "prose dark:prose-invert max-w-none transition-colors duration-200",
                        "opacity-80",
                      )}
                      animated={false}
                    >
                      {staticContent}
                    </Markdown>
                  )}
                  {hasStreamingContent && (
                    <Markdown
                      className={cn(
                        "prose dark:prose-invert max-w-none transition-colors duration-200",
                        "prose-primary",
                      )}
                      animated={true}
                    >
                      {streamingChunk}
                    </Markdown>
                  )}
                  {!hasStreamingContent && (
                    <Markdown
                      className={cn(
                        "prose dark:prose-invert max-w-none transition-colors duration-200",
                        isStreaming ? "prose-primary" : "opacity-80",
                      )}
                      animated={false}
                    >
                      {content}
                    </Markdown>
                  )}
                </ScrollContainer>
              </div>
            </CardContent>
          </Card>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

const GREETINGS = ["Cool", "Sounds great", "Looks good", "Great", "Awesome"];
function PlanCard({
  className,
  message,
  interruptMessage,
  onFeedback,
  waitForFeedback,
  onSendMessage,
}: {
  className?: string;
  message: Message;
  interruptMessage?: Message | null;
  onFeedback?: (feedback: { option: Option }) => void;
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
  waitForFeedback?: boolean;
}) {
  const t = useTranslations("chat.research");
  const plan = useMemo<{
    title?: string;
    thought?: string;
    steps?: { title?: string; description?: string; tools?: string[] }[];
  }>(() => {
    return parseJSON(message.content ?? "", {});
  }, [message.content]);

  const reasoningContent = message.reasoningContent;
  const hasMainContent = Boolean(
    message.content && message.content.trim() !== "",
  );

  // 判断是否正在思考：有推理内容但还没有主要内容
  const isThinking = Boolean(reasoningContent && !hasMainContent);

  // 判断是否应该显示计划：有主要内容就显示（无论是否还在流式传输）
  const shouldShowPlan = hasMainContent;
  const handleAccept = useCallback(async () => {
    if (onSendMessage) {
      onSendMessage(
        `${GREETINGS[Math.floor(Math.random() * GREETINGS.length)]}! ${Math.random() > 0.5 ? "Let's get started." : "Let's start."}`,
        {
          interruptFeedback: "accepted",
        },
      );
    }
  }, [onSendMessage]);
  return (
    <div className={cn("w-full", className)}>
      {reasoningContent && (
        <ThoughtBlock
          content={reasoningContent}
          isStreaming={isThinking}
          hasMainContent={hasMainContent}
          contentChunks={message.reasoningContentChunks}
        />
      )}
      {shouldShowPlan && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        >
          <Card className="w-full">
            <CardHeader>
              <CardTitle>
                <Markdown animated={false}>
                  {`### ${plan.title !== undefined && plan.title !== ""
                    ? plan.title
                    : t("deepResearch")
                    }`}
                </Markdown>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="break-words [word-break:break-word] [overflow-wrap:anywhere]">
                <Markdown className="opacity-80" animated={false}>
                  {plan.thought}
                </Markdown>
                {plan.steps && (
                  <ul className="my-2 flex list-decimal flex-col gap-4 border-l-[2px] pl-8">
                    {plan.steps.map((step, i) => (
                      <li key={`step-${i}`} className="break-words [word-break:break-word] [overflow-wrap:anywhere]">
                        <div className="flex items-start gap-2">
                          <div className="flex-1 min-w-0">
                            <h3 className="mb flex items-center gap-2 text-lg font-medium break-words [word-break:break-word]">
                              <Markdown animated={false}>
                                {step.title}
                              </Markdown>
                              {step.tools && step.tools.length > 0 && (
                                <Tooltip
                                  title={`Uses ${step.tools.length} MCP tool${step.tools.length > 1 ? "s" : ""}`}
                                >
                                  <div className="flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-800 shrink-0">
                                    <Wrench size={12} />
                                    <span>{step.tools.length}</span>
                                  </div>
                                </Tooltip>
                              )}
                            </h3>
                            <div className="text-muted-foreground text-sm break-words [word-break:break-word] [overflow-wrap:anywhere]">
                              <Markdown animated={false}>
                                {step.description}
                              </Markdown>
                            </div>
                            {step.tools && step.tools.length > 0 && (
                              <ToolsDisplay tools={step.tools} />
                            )}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </CardContent>
            <CardFooter className="flex justify-end">
              {!message.isStreaming && interruptMessage?.options?.length && (
                <motion.div
                  className="flex gap-2"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.3 }}
                >
                  {interruptMessage?.options.map((option) => (
                    <Button
                      key={option.value}
                      variant={
                        option.value === "accepted" ? "default" : "outline"
                      }
                      disabled={!waitForFeedback}
                      onClick={() => {
                        if (option.value === "accepted") {
                          void handleAccept();
                        } else {
                          onFeedback?.({
                            option,
                          });
                        }
                      }}
                    >
                      {option.text}
                    </Button>
                  ))}
                </motion.div>
              )}
            </CardFooter>
          </Card>
        </motion.div>
      )}
    </div>
  );
}

function PodcastCard({
  className,
  message,
}: {
  className?: string;
  message: Message;
}) {
  const data = useMemo(() => {
    return JSON.parse(message.content ?? "");
  }, [message.content]);
  const title = useMemo<string | undefined>(() => data?.title, [data]);
  const audioUrl = useMemo<string | undefined>(() => data?.audioUrl, [data]);
  const isGenerating = useMemo(() => {
    return message.isStreaming;
  }, [message.isStreaming]);
  const hasError = useMemo(() => {
    return data?.error !== undefined;
  }, [data]);
  const [isPlaying, setIsPlaying] = useState(false);
  return (
    <Card className={cn("w-[508px]", className)}>
      <CardHeader>
        <div className="text-muted-foreground flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            {isGenerating ? <LoadingOutlined /> : <Headphones size={16} />}
            {!hasError ? (
              <RainbowText animated={isGenerating}>
                {isGenerating
                  ? "Generating podcast..."
                  : isPlaying
                    ? "Now playing podcast..."
                    : "Podcast"}
              </RainbowText>
            ) : (
              <div className="text-red-500">
                Error when generating podcast. Please try again.
              </div>
            )}
          </div>
          {!hasError && !isGenerating && (
            <div className="flex">
              <Tooltip title="Download podcast">
                <Button variant="ghost" size="icon" asChild>
                  <a
                    href={audioUrl}
                    download={`${(title ?? "podcast").replaceAll(" ", "-")}.mp3`}
                  >
                    <Download size={16} />
                  </a>
                </Button>
              </Tooltip>
            </div>
          )}
        </div>
        <CardTitle>
          <div className="text-lg font-medium">
            <RainbowText animated={isGenerating}>{title}</RainbowText>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {audioUrl ? (
          <audio
            className="w-full"
            src={audioUrl}
            controls
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />
        ) : (
          <div className="w-full"></div>
        )}
      </CardContent>
    </Card>
  );
}

import type { ToolCallRuntime } from "~/core/messages/types";

function ToolsDisplay({ tools, toolCalls }: { tools?: string[]; toolCalls?: ToolCallRuntime[] }) {


  if (toolCalls && toolCalls.length > 0) {
    // Filter out tool calls with empty names
    const validToolCalls = toolCalls.filter(tool => tool.name && tool.name.trim());
    if (validToolCalls.length === 0) return null;

    return (
      <div className="mt-2 flex flex-col gap-2">
        {validToolCalls.map((tool, index) => {
          let jsonContent = null;
          if (tool.result) {
            try {
              const parsed = JSON.parse(tool.result);
              if (parsed && typeof parsed === 'object') {
                jsonContent = parsed;
              }
            } catch (e) {
              // Not JSON, ignore
            }
          }

          return (
            <Collapsible key={index} defaultOpen={false} className="flex flex-col gap-1 rounded-md border bg-muted/50 p-2 text-xs">
              <div className="flex items-center justify-between">
                <CollapsibleTrigger className="flex items-center gap-2 font-mono font-semibold text-muted-foreground w-full hover:text-foreground text-left cursor-pointer group">
                  <ChevronRight className="h-3 w-3 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-90" />
                  <span>🔧 {tool.name}</span>
                  {!tool.result && <span className="text-orange-500">(waiting...)</span>}
                </CollapsibleTrigger>
              </div>

              {tool.result && (
                <CollapsibleContent className="pl-5 border-l-2 border-muted-foreground/10 ml-1.5 mt-1 overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
                  {jsonContent ? (
                    <div className="rounded-md overflow-hidden text-xs my-1">
                      <SyntaxHighlighter
                        language="json"
                        style={vscDarkPlus}
                        customStyle={{ margin: 0, padding: '1rem', fontSize: '11px', lineHeight: '1.4' }}
                        wrapLongLines
                      >
                        {JSON.stringify(jsonContent, null, 2)}
                      </SyntaxHighlighter>
                    </div>
                  ) : (
                    <div className="font-mono text-muted-foreground/80 whitespace-pre-wrap py-1">
                      {tool.result}
                    </div>
                  )}
                </CollapsibleContent>
              )}
            </Collapsible>
          );
        })}
      </div>
    );
  }

  if (tools && tools.length > 0) {
    return (
      <div className="mt-2 flex flex-wrap gap-1">
        {tools.map((tool, index) => (
          <span
            key={index}
            className="rounded-md bg-muted px-2 py-1 text-xs font-mono text-muted-foreground"
          >
            {tool}
          </span>
        ))}
      </div>
    );
  }

  return null;
}
