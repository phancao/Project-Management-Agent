// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";

import { cn } from "~/lib/utils";

import { PMWelcome } from "./welcome";

export function ConversationStarter({
  className,
  onSend,
}: {
  className?: string;
  onSend?: (message: string) => void;
}) {
  const t = useTranslations("chat.pm");
  const questions = t.raw("conversationStarters") as string[];

  return (
    <div className={cn("flex w-full flex-col items-center gap-10 px-4 py-10", className)}>
      <PMWelcome className="w-full max-w-2xl transform transition-all duration-500 hover:scale-[1.01]" />
      <ul className="flex w-full flex-wrap justify-center gap-4 px-2">
        {questions.map((question, index) => (
          <motion.li
            key={`${index}-${question}`}
            className="w-full sm:w-[calc(50%-12px)] lg:w-[calc(33.33%-12px)] xl:w-[calc(25%-12px)] active:scale-95"
            style={{ transition: "all 0.2s ease-out" }}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{
              duration: 0.4,
              delay: index * 0.08 + 0.3,
              ease: [0.23, 1, 0.32, 1],
            }}
          >
            <div
              className="bg-card/50 hover:bg-card group relative h-full w-full cursor-pointer overflow-hidden rounded-3xl border border-indigo-500/20 dark:border-indigo-500/30 ring-1 ring-indigo-500/10 dark:ring-indigo-500/20 shadow-lg shadow-indigo-500/5 dark:shadow-xl dark:shadow-indigo-500/15 p-6 backdrop-blur-sm transition-all duration-300 hover:border-indigo-400/40 dark:hover:border-indigo-500/50 hover:ring-indigo-400/20 dark:hover:ring-indigo-500/30 hover:shadow-xl hover:shadow-indigo-400/15 dark:hover:shadow-indigo-500/25 hover:-translate-y-1"
              onClick={() => {
                onSend?.(question);
              }}
            >
              {/* Subtle gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-br from-brand/5 via-transparent to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />

              <div className="relative flex items-center justify-between gap-4">
                <span className="text-sm font-medium leading-relaxed text-foreground/80 transition-colors group-hover:text-foreground">
                  {question}
                </span>
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand/10 text-brand opacity-0 transition-all duration-300 group-hover:opacity-100 group-hover:translate-x-0 -translate-x-2">
                  <Plus size={16} />
                </div>
              </div>
            </div>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}
