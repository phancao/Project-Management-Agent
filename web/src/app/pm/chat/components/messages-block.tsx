// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";
import { FastForward, Play } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useRef, useState } from "react";

import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { fastForwardReplay } from "~/core/api";
import { useReplayMetadata } from "~/core/api/hooks";
import type { Option, Resource } from "~/core/messages";
import { useReplay } from "~/core/replay";
import { sendMessage, useMessageIds, useStore } from "~/core/store";
import { env } from "~/env";
import { cn } from "~/lib/utils";

import { ConversationStarter } from "./conversation-starter";
import { InputBox } from "./input-box";
import { MessageListView } from "./message-list-view";
import { Welcome } from "./welcome";

export function MessagesBlock({ className }: { className?: string }) {
  const t = useTranslations("chat.messages");
  const messageIds = useMessageIds();
  const messageCount = messageIds.length;
  const responding = useStore((state) => state.responding);
  // Note: openResearchId is no longer used for modal - AnalysisBlock shows inline
  const { isReplay } = useReplay();
  const { title: replayTitle, hasError: replayHasError } = useReplayMetadata();
  const [replayStarted, setReplayStarted] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [feedback, setFeedback] = useState<{ option: Option } | null>(null);
  const handleSend = useCallback(
    async (
      message: string,
      options?: {
        interruptFeedback?: string;
        resources?: Array<Resource>;
      },
    ) => {
      const abortController = new AbortController();
      abortControllerRef.current = abortController;
      try {
        await sendMessage(
          message,
          {
            interruptFeedback:
              options?.interruptFeedback ?? feedback?.option.value,
            resources: options?.resources,
          },
          {
            abortSignal: abortController.signal,
          },
        );
      } catch (error) {
        // Only log non-abort errors (abort is expected when user cancels)
        // Check for various abort error types and patterns
        const isAbortError =
          (error instanceof Error && error.name === 'AbortError') ||
          (error instanceof DOMException && error.name === 'AbortError') ||
          (error instanceof Error && (
            error.message?.toLowerCase().includes('abort') ||
            error.message?.toLowerCase().includes('aborted') ||
            error.message?.toLowerCase().includes('bodystreambuffer')
          )) ||
          (abortControllerRef.current?.signal.aborted === true);

        if (!isAbortError) {
          console.error('Failed to send message:', error);
        }
      } finally {
        // Clear the ref if it's still pointing to this controller
        if (abortControllerRef.current === abortController) {
          abortControllerRef.current = null;
        }
      }
    },
    [feedback],
  );
  const handleCancel = useCallback(() => {
    try {
      abortControllerRef.current?.abort();
    } catch (error) {
      // Suppress abort errors - they're expected when user cancels
      const isAbortError =
        (error instanceof Error && error.name === 'AbortError') ||
        (error instanceof DOMException && error.name === 'AbortError') ||
        (error instanceof Error && (
          error.message?.toLowerCase().includes('abort') ||
          error.message?.toLowerCase().includes('aborted') ||
          error.message?.toLowerCase().includes('bodystreambuffer')
        ));

      if (!isAbortError) {
        // Only log non-abort errors
        console.error('Error during cancel:', error);
      }
    } finally {
      abortControllerRef.current = null;
    }
  }, []);
  const handleFeedback = useCallback(
    (feedback: { option: Option }) => {
      setFeedback(feedback);
    },
    [setFeedback],
  );
  const handleRemoveFeedback = useCallback(() => {
    setFeedback(null);
  }, [setFeedback]);
  const handleStartReplay = useCallback(() => {
    setReplayStarted(true);
    void sendMessage();
  }, [setReplayStarted]);
  const [fastForwarding, setFastForwarding] = useState(false);
  const handleFastForwardReplay = useCallback(() => {
    setFastForwarding(!fastForwarding);
    fastForwardReplay(!fastForwarding);
  }, [fastForwarding]);
  return (
    <div className={cn("flex h-full w-full flex-col relative", className)}>
      <div className="flex grow overflow-hidden relative">
        {/* Always show MessageListView - AnalysisBlock displays inline */}
        <MessageListView
          className="flex h-full w-full"
          onFeedback={handleFeedback}
          onSendMessage={handleSend}
        />

        {!isReplay && !responding && messageCount === 0 && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-start bg-app/50 backdrop-blur-sm overflow-y-auto pt-10 md:pt-20">
            <ConversationStarter
              className="w-full max-w-none"
              onSend={handleSend}
            />
          </div>
        )}
      </div>

      {!isReplay ? (
        <div className="flex w-full shrink-0 flex-col px-4 pb-4 pt-0">
          <div className="relative min-h-[120px] h-auto w-full">
            <InputBox
              className="h-full w-full"
              responding={responding}
              feedback={feedback}
              onSend={handleSend}
              onCancel={handleCancel}
              onRemoveFeedback={handleRemoveFeedback}
            />
          </div>
        </div>
      ) : (
        <>
          <div
            className={cn(
              "fixed bottom-[calc(50vh+80px)] left-0 transition-all duration-500 ease-out",
              replayStarted && "pointer-events-none scale-150 opacity-0",
            )}
          >
            <Welcome />
          </div>
          <motion.div
            className="mb-4 h-fit w-full items-center justify-center"
            initial={{ opacity: 0, y: "20vh" }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Card
              className={cn(
                "w-full transition-all duration-300",
                !replayStarted && "translate-y-[-40vh]",
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex grow items-center">
                  {responding && (
                    <motion.div
                      className="ml-3"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      transition={{ duration: 0.3 }}
                    >
                      <video
                        // Walking deer animation, designed by @liangzhaojun. Thank you for creating it!
                        src="/images/walking_deer.webm"
                        autoPlay
                        loop
                        muted
                        className="h-[42px] w-[42px] object-contain"
                      />
                    </motion.div>
                  )}
                  <CardHeader className={cn("grow", responding && "pl-3")}>
                    <CardTitle>
                      <RainbowText animated={responding}>
                        {responding ? t("replaying") : `${replayTitle}`}
                      </RainbowText>
                    </CardTitle>
                    <CardDescription>
                      <RainbowText animated={responding}>
                        {responding
                          ? t("replayDescription")
                          : replayStarted
                            ? t("replayHasStopped")
                            : t("replayModeDescription")}
                      </RainbowText>
                    </CardDescription>
                  </CardHeader>
                </div>
                {!replayHasError && (
                  <div className="pr-4">
                    {responding && (
                      <Button
                        className={cn(fastForwarding && "animate-pulse")}
                        variant={fastForwarding ? "default" : "outline"}
                        onClick={handleFastForwardReplay}
                      >
                        <FastForward size={16} />
                        {t("fastForward")}
                      </Button>
                    )}
                    {!replayStarted && (
                      <Button className="w-24" onClick={handleStartReplay}>
                        <Play size={16} />
                        {t("play")}
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </Card>
            {!replayStarted && env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY && (
              <div className="text-muted-foreground w-full text-center text-xs">
                {t("demoNotice")}{" "}
                <a
                  className="underline"
                  href="https://github.com/bytedance/deer-flow"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t("clickHere")}
                </a>{" "}
                {t("cloneLocally")}
              </div>
            )}
          </motion.div>
        </>
      )}
    </div>
  );
}
