// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { MagicWandIcon } from "@radix-ui/react-icons";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Lightbulb, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useRef, useState } from "react";

import { AgentSelector } from "~/components/deer-flow/agent-selector";
import MessageInput, {
  type MessageInputRef,
} from "~/components/deer-flow/message-input";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { BorderBeam } from "~/components/magicui/border-beam";
import { Button } from "~/components/ui/button";
import { ContextTokenIndicator } from "~/components/chat/context-token-indicator";
import { enhancePrompt } from "~/core/api";
import { useConfig } from "~/core/api/hooks";
import type { Option, Resource } from "~/core/messages";
import {
  setEnableDeepThinking,
  useSettingsStore,
} from "~/core/store";
import { cn } from "~/lib/utils";

export function InputBox({
  className,
  responding,
  feedback,
  onSend,
  onCancel,
  onRemoveFeedback,
}: {
  className?: string;
  size?: "large" | "normal";
  responding?: boolean;
  feedback?: { option: Option } | null;
  onSend?: (
    message: string,
    options?: {
      interruptFeedback?: string;
      resources?: Array<Resource>;
    },
  ) => void;
  onCancel?: () => void;
  onRemoveFeedback?: () => void;
}) {
  const t = useTranslations("chat.inputBox");
  const tCommon = useTranslations("common");
  const enableDeepThinking = useSettingsStore(
    (state) => state.general.enableDeepThinking,
  );
  const { config, loading } = useConfig();
  const reportStyle = useSettingsStore((state) => state.general.reportStyle);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<MessageInputRef>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);

  // Enhancement state
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isEnhanceAnimating, setIsEnhanceAnimating] = useState(false);
  const [currentPrompt, setCurrentPrompt] = useState("");

  const handleSendMessage = useCallback(
    (message: string, resources: Array<Resource>) => {
      if (responding) {
        onCancel?.();
      } else {
        if (message.trim() === "") {
          return;
        }
        if (onSend) {
          onSend(message, {
            interruptFeedback: feedback?.option.value,
            resources,
          });
          onRemoveFeedback?.();
          // Clear enhancement animation after sending
          setIsEnhanceAnimating(false);
        }
      }
    },
    [responding, onCancel, onSend, feedback, onRemoveFeedback],
  );

  const handleEnhancePrompt = useCallback(async () => {
    if (currentPrompt.trim() === "" || isEnhancing) {
      return;
    }

    setIsEnhancing(true);
    setIsEnhanceAnimating(true);

    try {
      const enhancedPrompt = await enhancePrompt({
        prompt: currentPrompt,
        report_style: reportStyle.toUpperCase(),
      });

      // Add a small delay for better UX
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Update the input with the enhanced prompt with animation
      if (inputRef.current) {
        inputRef.current.setContent(enhancedPrompt);
        setCurrentPrompt(enhancedPrompt);
      }

      // Keep animation for a bit longer to show the effect
      setTimeout(() => {
        setIsEnhanceAnimating(false);
      }, 1000);
    } catch (error) {
      console.error("Failed to enhance prompt:", error);
      setIsEnhanceAnimating(false);
      // Could add toast notification here
    } finally {
      setIsEnhancing(false);
    }
  }, [currentPrompt, isEnhancing, reportStyle]);

  return (
    <div
      className={cn(
        "bg-background/95 dark:bg-card/45 relative flex h-full w-full flex-col rounded-2xl md:rounded-3xl backdrop-blur-md transition-all duration-300",
        "border border-indigo-500/20 dark:border-indigo-500/30",
        "ring-1 ring-indigo-500/10 dark:ring-indigo-500/20",
        "shadow-xl shadow-indigo-500/5 dark:shadow-2xl dark:shadow-indigo-500/15",
        "focus-within:border-indigo-400/40 dark:focus-within:border-indigo-500/50 focus-within:ring-indigo-400/20 dark:focus-within:ring-indigo-500/30",
        className,
      )}
      ref={containerRef}
    >
      <div className="w-full">
        <AnimatePresence>
          {feedback && (
            <motion.div
              ref={feedbackRef}
              className="bg-background/80 absolute top-0 left-0 z-30 mt-3 ml-5 flex items-center justify-center gap-2 rounded-full border border-brand/30 px-3 py-1 shadow-sm backdrop-blur-md"
              initial={{ opacity: 0, scale: 0.8, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.8, y: -10 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              <div className="text-brand flex h-full w-full items-center justify-center text-xs font-semibold uppercase tracking-wider opacity-90">
                {feedback.option.text}
              </div>
              <X
                className="cursor-pointer text-brand/60 transition-colors hover:text-brand"
                size={14}
                onClick={onRemoveFeedback}
              />
            </motion.div>
          )}
          {isEnhanceAnimating && (
            <motion.div
              className="pointer-events-none absolute inset-0 z-20 overflow-hidden rounded-[32px]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <div className="relative h-full w-full">
                {/* Refined Sparkle effect overlay */}
                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-brand/5 via-purple-500/5 to-brand/5"
                  animate={{
                    background: [
                      "linear-gradient(45deg, rgba(var(--brand), 0.05), rgba(147, 51, 234, 0.05), rgba(var(--brand), 0.05))",
                      "linear-gradient(225deg, rgba(147, 51, 234, 0.05), rgba(var(--brand), 0.05), rgba(147, 51, 234, 0.05))",
                      "linear-gradient(45deg, rgba(var(--brand), 0.05), rgba(147, 51, 234, 0.05), rgba(var(--brand), 0.05))",
                    ],
                  }}
                  transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                />
                {/* Floating refined sparkles */}
                {[...Array(8)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute h-1.5 w-1.5 rounded-full bg-brand/30 blur-[1px]"
                    style={{
                      left: `${15 + i * 10}%`,
                      top: `${20 + (i % 3) * 25}%`,
                    }}
                    animate={{
                      y: [-15, -30, -15],
                      opacity: [0, 0.8, 0],
                      scale: [0.3, 1.2, 0.3],
                    }}
                    transition={{
                      duration: 2.5,
                      repeat: Infinity,
                      delay: i * 0.15,
                      ease: "easeInOut",
                    }}
                  />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <MessageInput
          className={cn(
            "h-28 px-6 pt-6 text-base tracking-tight",
            feedback && "pt-12",
            isEnhanceAnimating && "transition-all duration-500",
          )}
          ref={inputRef}
          loading={loading}
          config={config}
          onEnter={handleSendMessage}
          onChange={setCurrentPrompt}
        />
      </div>
      <div className="flex flex-wrap items-center gap-3 px-6 py-4 min-h-fit mt-auto border-t border-border/30">
        <div className="flex flex-wrap grow items-center gap-2.5">
          {config?.models?.reasoning && config.models.reasoning.length > 0 && (
            <Tooltip
              className="max-w-60"
              title={
                <div>
                  <h3 className="mb-2 font-bold">
                    {t("deepThinkingTooltip.title", {
                      status: enableDeepThinking ? t("on") : t("off"),
                    })}
                  </h3>
                  <p>
                    {t("deepThinkingTooltip.description", {
                      model: config.models.reasoning[0] ?? "",
                    })}
                  </p>
                </div>
              }
            >
              <Button
                className={cn(
                  "rounded-full shrink-0 h-9 px-4 text-xs font-semibold transition-all duration-300",
                  enableDeepThinking
                    ? "bg-brand/20 dark:bg-brand/10 border-brand/50 text-brand shadow-sm shadow-brand/10"
                    : "bg-gray-100 dark:bg-muted-foreground/5 border-gray-200 dark:border-transparent text-gray-600 dark:text-muted-foreground hover:bg-gray-200 dark:hover:bg-muted-foreground/10",
                )}
                variant="outline"
                onClick={() => {
                  setEnableDeepThinking(!enableDeepThinking);
                }}
              >
                <Lightbulb size={14} className={cn("mr-1.5", enableDeepThinking && "animate-pulse")} /> {t("deepThinking")}
              </Button>
            </Tooltip>
          )}

          <AgentSelector />

          {/* Context Token Indicator */}
          <ContextTokenIndicator className="ml-auto sm:ml-2 opacity-60 hover:opacity-100 transition-opacity" />
        </div>
        <div className="flex shrink-0 items-center gap-3 ml-auto">
          <Tooltip title={t("enhancePrompt")}>
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "h-10 w-10 rounded-full bg-gray-100 dark:bg-muted-foreground/5 hover:bg-brand/10 border border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/20 transition-all duration-300",
                isEnhancing && "animate-pulse",
                !isEnhancing && currentPrompt.trim() !== "" && "hover:border-brand/40 hover:shadow-xl hover:shadow-brand/30"
              )}
              onClick={handleEnhancePrompt}
              disabled={isEnhancing || currentPrompt.trim() === ""}
            >
              {isEnhancing ? (
                <div className="flex h-10 w-10 items-center justify-center">
                  <div className="bg-brand/70 h-3 w-3 animate-bounce rounded-full" />
                </div>
              ) : (
                <MagicWandIcon className={cn("transition-colors", currentPrompt.trim() !== "" ? "text-brand" : "text-muted-foreground/40")} />
              )}
            </Button>
          </Tooltip>
          <Tooltip title={responding ? tCommon("stop") : tCommon("send")}>
            <Button
              variant={currentPrompt.trim() !== "" || responding ? "default" : "outline"}
              size="icon"
              className={cn(
                "h-10 w-10 rounded-full transition-all duration-500",
                currentPrompt.trim() !== "" && !responding && "bg-brand hover:bg-brand/90 text-white scale-110 shadow-lg shadow-brand/40 hover:shadow-xl hover:shadow-brand/50",
                responding && "bg-destructive hover:bg-destructive/90 text-white shadow-lg shadow-destructive/40",
                currentPrompt.trim() === "" && !responding && "border border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/20"
              )}
              onClick={() => inputRef.current?.submit()}
            >
              {responding ? (
                <div className="flex h-10 w-10 items-center justify-center">
                  <div className="bg-white h-3 w-3 rounded-sm" />
                </div>
              ) : (
                <ArrowUp className={cn("transition-all", currentPrompt.trim() !== "" ? "scale-110" : "opacity-40")} />
              )}
            </Button>
          </Tooltip>
        </div>
      </div>
      {isEnhancing && (
        <div className="absolute inset-0 pointer-events-none rounded-[32px] overflow-hidden">
          <BorderBeam
            duration={4}
            size={300}
            className="from-transparent via-brand/50 to-transparent"
          />
          <BorderBeam
            duration={4}
            delay={2}
            size={300}
            className="from-transparent via-purple-500/50 to-transparent"
          />
        </div>
      )}
    </div>
  );
}
