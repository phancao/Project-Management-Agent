// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useEffect, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";

import { ProviderManagementView } from "./views/provider-management-view";

export function ProviderManagementDialog() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handleShowProviders = () => {
      setOpen(true);
    };

    window.addEventListener("pm_show_providers", handleShowProviders);
    return () => {
      window.removeEventListener("pm_show_providers", handleShowProviders);
    };
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Provider Management</DialogTitle>
        </DialogHeader>
        <ProviderManagementView />
      </DialogContent>
    </Dialog>
  );
}
