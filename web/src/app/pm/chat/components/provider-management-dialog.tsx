// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useEffect, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";

import { ProviderManagementView } from "./views/provider-management-view";

export function ProviderManagementDialog() {
  const [open, setOpen] = useState(false);
  const [defaultTab, setDefaultTab] = useState<"pm" | "ai" | "search">("pm");

  useEffect(() => {
    const handleShowProviders = (event?: CustomEvent) => {
      setOpen(true);
      // Check if we should open AI Providers tab
      if (event?.detail?.tab === "ai") {
        setDefaultTab("ai");
      } else {
        setDefaultTab("pm");
      }
    };

    window.addEventListener("pm_show_providers", handleShowProviders as EventListener);
    return () => {
      window.removeEventListener("pm_show_providers", handleShowProviders as EventListener);
    };
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Provider Management</DialogTitle>
          <DialogDescription>
            Manage your project management provider connections and view available projects.
          </DialogDescription>
        </DialogHeader>
        <ProviderManagementView defaultTab={defaultTab} />
      </DialogContent>
    </Dialog>
  );
}
