// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useState } from "react";

import { Plus } from "lucide-react";

import { Button } from "~/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Textarea } from "~/components/ui/textarea";
import { resolveServiceURL } from "~/core/api/resolve-service-url";

interface CreateEpicDialogProps {
  projectId: string | null | undefined;
  onEpicCreated?: () => void;
}

export function CreateEpicDialog({ projectId, onEpicCreated }: CreateEpicDialogProps) {
  const [open, setOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
  });
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!projectId) {
      setError("No project selected");
      return;
    }

    if (!formData.name.trim()) {
      setError("Epic name is required");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        resolveServiceURL(`pm/projects/${encodeURIComponent(projectId)}/epics`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: formData.name.trim(),
            description: formData.description.trim() ?? undefined,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail ?? `Failed to create epic: ${response.statusText}`);
      }

      // Reset form and close dialog
      setFormData({ name: "", description: "" });
      setOpen(false);
      
      // Trigger refresh
      if (onEpicCreated) {
        onEpicCreated();
      }
      window.dispatchEvent(new CustomEvent("pm_refresh", { 
        detail: { type: "pm_refresh" } 
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create epic");
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen && !isLoading) {
      // Reset form when closing
      setFormData({ name: "", description: "" });
      setError(null);
    }
    setOpen(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="w-full" disabled={!projectId}>
          <Plus className="w-4 h-4 mr-2" />
          Create epic
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Create Epic</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label htmlFor="epic-name">Epic Name *</Label>
            <Input
              id="epic-name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Enter epic name"
              disabled={isLoading}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="epic-description">Description</Label>
            <Textarea
              id="epic-description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Enter epic description (optional)"
              disabled={isLoading}
              rows={4}
            />
          </div>

          {error && (
            <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-3 rounded-md">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading || !formData.name.trim()}>
              {isLoading ? "Creating..." : "Create Epic"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
