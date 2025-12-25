// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { LoadingOutlined } from "@ant-design/icons";
import { motion } from "framer-motion";
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

import { PlannerAnalysisBlock } from "./analysis-block";
import { ReActAnalysisBlock } from "./react-analysis-block";
import { HandoverIndicator } from "./handover-indicator";

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
  const messageIds = useRenderableMessageIds();
  const interruptMessage = useLastInterruptMessage();
  const waitingForFeedbackMessageId = useLastFeedbackMessageId();
  const responding = useStore((state) => state.responding);
  const noOngoingResearch = useStore(
    (state) => state.ongoingResearchId === null,
  );
  const ongoingResearchIsOpen = useStore(
    (state) => state.ongoingResearchId === state.openResearchId,
  );

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
        {messageIds.map((messageId) => (
          <MessageListItem
            key={messageId}
            messageId={messageId}
            waitForFeedback={waitingForFeedbackMessageId === messageId}
            interruptMessage={interruptMessage}
            onFeedback={onFeedback}
            onSendMessage={onSendMessage}
            onToggleResearch={handleToggleResearch}
          />
        ))}
        <div className="flex h-8 w-full shrink-0"></div>
      </ul>
      {responding && (noOngoingResearch || !ongoingResearchIsOpen) && (
        <LoadingAnimation className="w-full" />
      )}
    </ScrollContainer>
  );
}

function MessageListItem({
  className,
  messageId,
  waitForFeedback,
  interruptMessage,
  onFeedback,
  onSendMessage,
  onToggleResearch,
}: {
  className?: string;
  messageId: string;
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
    // DEBUG: Log when startOfResearch changes
    if (isStart) {
      console.log(`[DEBUG-RENDER] ✅ startOfResearch=true for messageId: ${messageId}`, {
        researchIds: Array.from(validResearchIds),
        timestamp: new Date().toISOString()
      });
    }
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
      console.log(`[DEBUG-RENDER] 🚫 Skipping planner message ${message.id} (part of research block)`, new Error().stack);
      return null;
    }

    if (
      message.role === "user" ||
      message.agent === "coordinator" ||
      message.agent === "planner" ||
      message.agent === "podcast" ||
      message.agent === "react_agent" ||  // NEW: Handle ReAct agent messages
      startOfResearch
      // Note: reporter is NOT included here - report is shown inside AnalysisBlock
    ) {
      let content: React.ReactNode;

      // Priority 1: If this is the start of research, route to correct component based on agent
      if (startOfResearch && message?.id) {
        const state = useStore.getState();
        const isReactAgent = message.agent === "react_agent";
        const isPlanner = message.agent === "planner";
        const escalationLink = state.reactToPlannerEscalation.get(message.id);

        // Phase 4: Route based on agent type and escalation
        if (isReactAgent && escalationLink) {
          // Escalation: Show both ReAct (left) and Planner (right) side-by-side with handover indicator
          console.log(`[DEBUG-RENDER] 🔄 Rendering escalation: ReAct=${message.id} → Planner=${escalationLink}`);
          content = (
            <div className="w-full px-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ReActAnalysisBlock researchId={message.id} />
                <PlannerAnalysisBlock researchId={escalationLink} />
              </div>
              <HandoverIndicator className="mt-4" />
            </div>
          );
        } else if (isReactAgent) {
          // ReAct agent: Use ReActAnalysisBlock (token-by-token streaming)
          console.log(`[DEBUG-RENDER] ⚡ Rendering ReActAnalysisBlock for message ${message.id}`);
          content = (
            <div className="w-full px-4">
              <ReActAnalysisBlock researchId={message.id} />
            </div>
          );
        } else if (isPlanner) {
          // Planner agent: Use PlannerAnalysisBlock (JSON plan parsing)
          console.log(`[DEBUG-RENDER] 📋 Rendering PlannerAnalysisBlock for message ${message.id}`);
          content = (
            <div className="w-full px-4">
              <PlannerAnalysisBlock researchId={message.id} />
            </div>
          );
        } else {
          // Fallback: Use PlannerAnalysisBlock for other agents (backward compatibility)
          console.log(`[DEBUG-RENDER] 📋 Rendering PlannerAnalysisBlock (fallback) for message ${message.id}, agent=${message.agent}`);
          content = (
            <div className="w-full px-4">
              <PlannerAnalysisBlock researchId={message.id} />
            </div>
          );
        }
      } else if (message.agent === "planner") {
        console.log(`[DEBUG-RENDER] 📋 Rendering PlanCard for message ${message.id} (standalone planner)`, new Error().stack);
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
        console.log(`[DEBUG-RENDER] 🎙️ Rendering PodcastCard for message ${message.id}`, new Error().stack);
        content = (
          <div className="w-full px-4">
            <PodcastCard message={message} />
          </div>
        );
      } else {
        console.log(`[DEBUG-RENDER] 💬 Rendering MessageBubble for message ${message.id} (agent: ${message.agent}, role: ${message.role})`, new Error().stack);
        // Render if there's content OR if it's streaming (content may be accumulating)
        content = (message.content || message.isStreaming) ? (
          <div
            className={cn(
              "flex w-full px-4",
              message.role === "user" && "justify-end",
              className,
            )}
          >
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

function ToolsDisplay({ tools }: { tools: string[] }) {
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
