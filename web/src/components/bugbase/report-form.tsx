// Copyright (c) 2025 Galaxy Technology Service
// BugBase Report Form - Modal form for submitting bug reports

"use client";

import { useState, useCallback, useRef } from "react";
import { X, Send, Loader2, AlertTriangle, ExternalLink, Upload, Camera } from "lucide-react";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea";
import { Label } from "~/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "~/components/ui/select";
import { cn } from "~/lib/utils";
import { useCardGlow } from "~/core/hooks/use-theme-colors";
import type { ScreenshotResult } from "~/core/bugbase/screenshot-service";
import type { NavigationEntry } from "~/core/bugbase/navigation-tracker";

interface ReportFormProps {
    screenshot: ScreenshotResult | null;
    navigationHistory: NavigationEntry[];
    onClose: () => void;
}

type Severity = "low" | "medium" | "high" | "critical";

const SEVERITY_OPTIONS: { value: Severity; label: string; color: string }[] = [
    { value: "low", label: "Low", color: "text-blue-500" },
    { value: "medium", label: "Medium", color: "text-yellow-500" },
    { value: "high", label: "High", color: "text-orange-500" },
    { value: "critical", label: "Critical", color: "text-red-500" },
];

export function ReportForm({ screenshot: initialScreenshot, navigationHistory, onClose }: ReportFormProps) {
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [severity, setSeverity] = useState<Severity>("medium");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showNavHistory, setShowNavHistory] = useState(false);
    const [screenshot, setScreenshot] = useState<ScreenshotResult | null>(initialScreenshot);
    const [manualImageUrl, setManualImageUrl] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const cardGlow = useCardGlow();

    const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            const dataUrl = event.target?.result as string;
            setManualImageUrl(dataUrl);
            // Create a screenshot-like object
            const img = new Image();
            img.onload = () => {
                setScreenshot({
                    dataUrl,
                    width: img.width,
                    height: img.height,
                    timestamp: Date.now(),
                });
            };
            img.src = dataUrl;
        };
        reader.readAsDataURL(file);
    }, []);

    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();

        if (!title.trim()) {
            setError("Title is required");
            return;
        }

        setIsSubmitting(true);
        setError(null);

        try {
            const response = await fetch("/api/bugbase/report", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: title.trim(),
                    description: description.trim(),
                    severity,
                    screenshot: screenshot?.dataUrl || manualImageUrl || null,
                    navigationHistory: navigationHistory.slice(-20), // Last 20 entries
                    pageUrl: typeof window !== "undefined" ? window.location.href : "",
                    userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.message || "Failed to submit bug report");
            }

            // Success - close form
            onClose();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to submit report");
        } finally {
            setIsSubmitting(false);
        }
    }, [title, description, severity, screenshot, manualImageUrl, navigationHistory, onClose]);

    const recentNav = navigationHistory.slice(-5).reverse();
    const hasImage = screenshot || manualImageUrl;

    return (
        <div
            data-bugbase-ignore
            className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/50 backdrop-blur-sm"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className={cn(
                "w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-background shadow-2xl",
                cardGlow.className
            )}>
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                    <div className="flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-brand" />
                        <h2 className="text-lg font-semibold">Report a Bug</h2>
                    </div>
                    <Button variant="ghost" size="icon" onClick={onClose}>
                        <X className="w-4 h-4" />
                    </Button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    {/* Screenshot Section */}
                    <div className="space-y-2">
                        <Label>Screenshot</Label>
                        {hasImage ? (
                            <div className="relative rounded-lg border border-border overflow-hidden bg-muted/30">
                                <img
                                    src={screenshot?.dataUrl || manualImageUrl || ""}
                                    alt="Bug screenshot"
                                    className="w-full h-auto max-h-48 object-contain"
                                />
                                <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/60 rounded text-xs text-white">
                                    {screenshot ? `${screenshot.width} x ${screenshot.height}` : "Uploaded"}
                                </div>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setScreenshot(null);
                                        setManualImageUrl(null);
                                    }}
                                    className="absolute top-2 right-2 p-1 bg-red-500 rounded-full text-white hover:bg-red-600"
                                >
                                    <X className="w-3 h-3" />
                                </button>
                            </div>
                        ) : (
                            <div
                                onClick={() => fileInputRef.current?.click()}
                                className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-brand/50 hover:bg-brand/5 transition-colors"
                            >
                                <Upload className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                                <p className="text-sm text-muted-foreground">
                                    Auto-capture failed. Click to upload a screenshot.
                                </p>
                                <p className="text-xs text-muted-foreground mt-1">
                                    (PNG, JPG, or GIF)
                                </p>
                            </div>
                        )}
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleFileUpload}
                            className="hidden"
                        />
                    </div>

                    {/* Title */}
                    <div className="space-y-2">
                        <Label htmlFor="title">Title *</Label>
                        <Input
                            id="title"
                            placeholder="Brief description of the issue..."
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            className={cn(error && !title.trim() && "border-red-500")}
                        />
                    </div>

                    {/* Description */}
                    <div className="space-y-2">
                        <Label htmlFor="description">Description</Label>
                        <Textarea
                            id="description"
                            placeholder="Steps to reproduce, expected behavior, actual behavior..."
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={4}
                        />
                    </div>

                    {/* Severity */}
                    <div className="space-y-2">
                        <Label>Severity</Label>
                        <Select value={severity} onValueChange={(v) => setSeverity(v as Severity)}>
                            <SelectTrigger className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {SEVERITY_OPTIONS.map((opt) => (
                                    <SelectItem key={opt.value} value={opt.value}>
                                        <span className={opt.color}>{opt.label}</span>
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Navigation History */}
                    <div className="space-y-2">
                        <button
                            type="button"
                            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
                            onClick={() => setShowNavHistory(!showNavHistory)}
                        >
                            <ExternalLink className="w-3 h-3" />
                            Navigation History ({navigationHistory.length} steps)
                        </button>
                        {showNavHistory && recentNav.length > 0 && (
                            <div className="text-xs bg-muted/30 rounded-lg p-3 space-y-1 max-h-32 overflow-y-auto">
                                {recentNav.map((entry, idx) => (
                                    <div key={entry.id} className="flex items-center gap-2 text-muted-foreground">
                                        <span className="w-4 text-center">{recentNav.length - idx}.</span>
                                        <span className="font-mono truncate flex-1">{entry.path}</span>
                                        <span className="text-xs opacity-60">
                                            {new Date(entry.timestamp).toLocaleTimeString()}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="px-4 py-3 rounded-lg bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex justify-end gap-3 pt-2">
                        <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isSubmitting}>
                            {isSubmitting ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Submitting...
                                </>
                            ) : (
                                <>
                                    <Send className="w-4 h-4 mr-2" />
                                    Submit Report
                                </>
                            )}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
