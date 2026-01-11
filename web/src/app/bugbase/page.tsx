// Copyright (c) 2025 Galaxy Technology Service
// BugBase Admin Page - View and manage bug reports

"use client";

import { useState, useEffect, useCallback } from "react";
import { Bug, RefreshCw, ExternalLink, MessageSquare, CheckCircle, Clock, AlertTriangle, XCircle, Image, ChevronRight, Layers } from "lucide-react";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Badge } from "~/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "~/components/ui/select";
import { cn } from "~/lib/utils";
import { useCardGlow } from "~/core/hooks/use-theme-colors";

interface BugData {
    id: string;
    title: string;
    description: string | null;
    severity: string;
    status: string;
    screenshot_path: string | null;
    navigation_history: Array<{ path: string; action: string; timestamp: number }> | null;
    page_url: string | null;
    user_agent: string | null;
    created_at: string;
    updated_at: string;
    comments?: Array<{
        id: string;
        content: string;
        author: string;
        created_at: string;
    }>;
}

const BUGBASE_API_URL = process.env.NEXT_PUBLIC_BUGBASE_URL || "http://localhost:8082";

const STATUS_CONFIG = {
    open: { label: "Open", icon: AlertTriangle, color: "text-orange-500", bgColor: "bg-orange-500/10 border-orange-500/20" },
    in_progress: { label: "In Progress", icon: Clock, color: "text-blue-500", bgColor: "bg-blue-500/10 border-blue-500/20" },
    fixed: { label: "Fixed", icon: CheckCircle, color: "text-green-500", bgColor: "bg-green-500/10 border-green-500/20" },
    closed: { label: "Closed", icon: XCircle, color: "text-gray-500", bgColor: "bg-gray-500/10 border-gray-500/20" },
};

const SEVERITY_CONFIG = {
    low: { label: "Low", color: "text-blue-600", bgColor: "bg-blue-100 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800" },
    medium: { label: "Medium", color: "text-yellow-600", bgColor: "bg-yellow-100 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800" },
    high: { label: "High", color: "text-orange-600", bgColor: "bg-orange-100 dark:bg-orange-900/30 border-orange-200 dark:border-orange-800" },
    critical: { label: "Critical", color: "text-red-600", bgColor: "bg-red-100 dark:bg-red-900/30 border-red-200 dark:border-red-800" },
};

export default function BugBasePage() {
    const [bugs, setBugs] = useState<BugData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filterStatus, setFilterStatus] = useState<string>("all");
    const [filterSeverity, setFilterSeverity] = useState<string>("all");
    const [selectedBug, setSelectedBug] = useState<BugData | null>(null);
    const [imageModalOpen, setImageModalOpen] = useState(false);
    const cardGlow = useCardGlow();

    const fetchBugs = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams();
            if (filterStatus !== "all") params.set("status", filterStatus);
            if (filterSeverity !== "all") params.set("severity", filterSeverity);

            const response = await fetch(`${BUGBASE_API_URL}/api/bugs?${params}`);
            if (!response.ok) throw new Error("Failed to fetch bugs");

            const data = await response.json();
            setBugs(data.bugs || []);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load bugs");
        } finally {
            setLoading(false);
        }
    }, [filterStatus, filterSeverity]);

    const fetchBugDetails = useCallback(async (bugId: string) => {
        // Toggle: if clicking same bug, deselect it
        if (selectedBug?.id === bugId) {
            setSelectedBug(null);
            return;
        }

        try {
            const response = await fetch(`${BUGBASE_API_URL}/api/bugs/${bugId}`);
            if (!response.ok) throw new Error("Failed to fetch bug details");

            const data = await response.json();
            setSelectedBug(data);
        } catch (err) {
            console.error("Failed to fetch bug details:", err);
        }
    }, [selectedBug?.id]);

    const updateBugStatus = useCallback(async (bugId: string, status: string) => {
        try {
            const response = await fetch(`${BUGBASE_API_URL}/api/bugs/${bugId}/status`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status }),
            });
            if (!response.ok) throw new Error("Failed to update status");

            fetchBugs();
            if (selectedBug?.id === bugId) {
                fetchBugDetails(bugId);
            }
        } catch (err) {
            console.error("Failed to update bug status:", err);
        }
    }, [fetchBugs, fetchBugDetails, selectedBug]);

    useEffect(() => {
        fetchBugs();
    }, [fetchBugs]);

    // Stats
    const openCount = bugs.filter(b => b.status === "open").length;
    const inProgressCount = bugs.filter(b => b.status === "in_progress").length;
    const fixedCount = bugs.filter(b => b.status === "fixed").length;

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
            {/* Header */}
            <div className="sticky top-0 z-10 backdrop-blur-xl bg-white/70 dark:bg-slate-900/70 border-b border-slate-200/50 dark:border-slate-700/50">
                <div className="max-w-7xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="p-2.5 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 shadow-lg shadow-orange-500/25">
                                <Bug className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-xl font-bold bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-300 bg-clip-text text-transparent">
                                    BugBase
                                </h1>
                                <p className="text-xs text-muted-foreground">Self-Improvement Bug Tracker</p>
                            </div>
                        </div>
                        <Button onClick={fetchBugs} variant="outline" size="sm" className="gap-2">
                            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                            Refresh
                        </Button>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
                {/* Stats Cards */}
                <div className="grid grid-cols-4 gap-4">
                    <Card className={cn("border-l-4 border-l-slate-400", cardGlow.className)}>
                        <CardContent className="py-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-2xl font-bold">{bugs.length}</p>
                                    <p className="text-xs text-muted-foreground">Total Bugs</p>
                                </div>
                                <Layers className="w-8 h-8 text-slate-400" />
                            </div>
                        </CardContent>
                    </Card>
                    <Card className={cn("border-l-4 border-l-orange-400", cardGlow.className)}>
                        <CardContent className="py-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-2xl font-bold text-orange-600">{openCount}</p>
                                    <p className="text-xs text-muted-foreground">Open</p>
                                </div>
                                <AlertTriangle className="w-8 h-8 text-orange-400" />
                            </div>
                        </CardContent>
                    </Card>
                    <Card className={cn("border-l-4 border-l-blue-400", cardGlow.className)}>
                        <CardContent className="py-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-2xl font-bold text-blue-600">{inProgressCount}</p>
                                    <p className="text-xs text-muted-foreground">In Progress</p>
                                </div>
                                <Clock className="w-8 h-8 text-blue-400" />
                            </div>
                        </CardContent>
                    </Card>
                    <Card className={cn("border-l-4 border-l-green-400", cardGlow.className)}>
                        <CardContent className="py-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-2xl font-bold text-green-600">{fixedCount}</p>
                                    <p className="text-xs text-muted-foreground">Fixed</p>
                                </div>
                                <CheckCircle className="w-8 h-8 text-green-400" />
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Filters */}
                <Card className={cn("border-0 shadow-sm", cardGlow.className)}>
                    <CardContent className="py-3">
                        <div className="flex items-center gap-4">
                            <Select value={filterStatus} onValueChange={setFilterStatus}>
                                <SelectTrigger className="w-36 h-9">
                                    <SelectValue placeholder="Status" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Statuses</SelectItem>
                                    <SelectItem value="open">Open</SelectItem>
                                    <SelectItem value="in_progress">In Progress</SelectItem>
                                    <SelectItem value="fixed">Fixed</SelectItem>
                                    <SelectItem value="closed">Closed</SelectItem>
                                </SelectContent>
                            </Select>

                            <Select value={filterSeverity} onValueChange={setFilterSeverity}>
                                <SelectTrigger className="w-36 h-9">
                                    <SelectValue placeholder="Severity" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Severities</SelectItem>
                                    <SelectItem value="critical">Critical</SelectItem>
                                    <SelectItem value="high">High</SelectItem>
                                    <SelectItem value="medium">Medium</SelectItem>
                                    <SelectItem value="low">Low</SelectItem>
                                </SelectContent>
                            </Select>

                            <div className="flex-1" />
                            <Badge variant="secondary" className="font-normal">
                                {bugs.length} bug{bugs.length !== 1 ? "s" : ""} found
                            </Badge>
                        </div>
                    </CardContent>
                </Card>

                {/* Error State */}
                {error && (
                    <div className="px-4 py-3 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm">
                        {error}
                    </div>
                )}

                {/* Bug List & Detail View */}
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                    {/* Bug List */}
                    <div className="lg:col-span-2 space-y-3">
                        {loading && bugs.length === 0 ? (
                            <div className="text-center py-16 text-muted-foreground">
                                <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin opacity-50" />
                                Loading bugs...
                            </div>
                        ) : bugs.length === 0 ? (
                            <div className="text-center py-16">
                                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
                                <p className="text-lg font-medium">No bugs found!</p>
                                <p className="text-sm text-muted-foreground">Great job! 🎉</p>
                            </div>
                        ) : (
                            bugs.map((bug) => {
                                const statusConfig = STATUS_CONFIG[bug.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.open;
                                const severityConfig = SEVERITY_CONFIG[bug.severity as keyof typeof SEVERITY_CONFIG] || SEVERITY_CONFIG.medium;
                                const StatusIcon = statusConfig.icon;
                                const isSelected = selectedBug?.id === bug.id;

                                return (
                                    <Card
                                        key={bug.id}
                                        onClick={() => fetchBugDetails(bug.id)}
                                        className={cn(
                                            "cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-[1.01] border",
                                            isSelected
                                                ? "ring-2 ring-brand shadow-lg border-brand/30"
                                                : "hover:border-slate-300 dark:hover:border-slate-600",
                                            cardGlow.className
                                        )}
                                    >
                                        <CardContent className="p-4">
                                            <div className="flex items-start gap-3">
                                                <div className={cn("p-2 rounded-lg border", statusConfig.bgColor)}>
                                                    <StatusIcon className={cn("w-4 h-4", statusConfig.color)} />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <h3 className="font-medium truncate text-sm">{bug.title}</h3>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <Badge variant="outline" className={cn("text-xs px-2 py-0", severityConfig.color, severityConfig.bgColor)}>
                                                            {severityConfig.label}
                                                        </Badge>
                                                        <span className="text-xs text-muted-foreground">
                                                            {new Date(bug.created_at).toLocaleDateString()}
                                                        </span>
                                                    </div>
                                                </div>
                                                {bug.screenshot_path && (
                                                    <div className="flex-shrink-0 w-14 h-10 rounded-lg border border-border overflow-hidden bg-muted/30 shadow-sm">
                                                        <img
                                                            src={`${BUGBASE_API_URL}/api/screenshots/${bug.screenshot_path.split('/').pop()}`}
                                                            alt="Screenshot"
                                                            className="w-full h-full object-cover"
                                                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                                        />
                                                    </div>
                                                )}
                                                <ChevronRight className={cn(
                                                    "w-4 h-4 text-muted-foreground transition-transform",
                                                    isSelected && "transform rotate-90"
                                                )} />
                                            </div>
                                        </CardContent>
                                    </Card>
                                );
                            })
                        )}
                    </div>

                    {/* Bug Detail */}
                    <div className="lg:col-span-3">
                        {selectedBug ? (
                            <Card className={cn("sticky top-24 border-0 shadow-lg", cardGlow.className)}>
                                <CardHeader className="pb-4 border-b border-border/50">
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1">
                                            <CardTitle className="text-lg mb-1">{selectedBug.title}</CardTitle>
                                            <CardDescription className="font-mono text-xs">
                                                ID: {selectedBug.id.slice(0, 8)}...
                                            </CardDescription>
                                        </div>
                                        <Select
                                            value={selectedBug.status}
                                            onValueChange={(v) => updateBugStatus(selectedBug.id, v)}
                                        >
                                            <SelectTrigger className={cn(
                                                "w-32 h-9",
                                                STATUS_CONFIG[selectedBug.status as keyof typeof STATUS_CONFIG]?.bgColor
                                            )}>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="open">Open</SelectItem>
                                                <SelectItem value="in_progress">In Progress</SelectItem>
                                                <SelectItem value="fixed">Fixed</SelectItem>
                                                <SelectItem value="closed">Closed</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </CardHeader>
                                <CardContent className="pt-4 space-y-5">
                                    {/* Description */}
                                    {selectedBug.description && (
                                        <div>
                                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Description</h4>
                                            <p className="text-sm leading-relaxed">{selectedBug.description}</p>
                                        </div>
                                    )}

                                    {/* Page URL */}
                                    {selectedBug.page_url && (
                                        <div>
                                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Page URL</h4>
                                            <a
                                                href={selectedBug.page_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-sm text-brand hover:underline flex items-center gap-1.5 font-mono"
                                            >
                                                <ExternalLink className="w-3.5 h-3.5" />
                                                {selectedBug.page_url.length > 60
                                                    ? selectedBug.page_url.slice(0, 60) + "..."
                                                    : selectedBug.page_url}
                                            </a>
                                        </div>
                                    )}

                                    {/* Screenshot */}
                                    {selectedBug.screenshot_path && (
                                        <div>
                                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Screenshot</h4>
                                            <div
                                                className="relative rounded-xl border border-border overflow-hidden bg-gradient-to-br from-slate-100 to-slate-50 dark:from-slate-800 dark:to-slate-900 shadow-inner cursor-pointer group"
                                                onClick={() => setImageModalOpen(true)}
                                            >
                                                <img
                                                    src={`${BUGBASE_API_URL}/api/screenshots/${selectedBug.screenshot_path.split('/').pop()}`}
                                                    alt="Bug screenshot"
                                                    className="w-full h-auto max-h-72 object-contain transition-transform group-hover:scale-[1.02]"
                                                />
                                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center">
                                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity px-3 py-1.5 bg-black/70 rounded-lg text-xs text-white flex items-center gap-1.5">
                                                        <Image className="w-3.5 h-3.5" />
                                                        Click to expand
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Navigation History */}
                                    {selectedBug.navigation_history && selectedBug.navigation_history.length > 0 && (
                                        <div>
                                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                                                Navigation History ({selectedBug.navigation_history.length} steps)
                                            </h4>
                                            <div className="text-xs font-mono bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 max-h-32 overflow-y-auto space-y-1 border border-slate-200 dark:border-slate-700">
                                                {selectedBug.navigation_history.slice(-10).map((step, idx) => (
                                                    <div key={idx} className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
                                                        <span className="w-4 text-right opacity-50">{idx + 1}.</span>
                                                        <span className="truncate">{step.path}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Comments */}
                                    {selectedBug.comments && selectedBug.comments.length > 0 && (
                                        <div>
                                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                                <MessageSquare className="w-3.5 h-3.5" />
                                                Comments ({selectedBug.comments.length})
                                            </h4>
                                            <div className="space-y-2">
                                                {selectedBug.comments.map((comment) => (
                                                    <div
                                                        key={comment.id}
                                                        className={cn(
                                                            "text-sm p-3 rounded-lg border",
                                                            comment.author === "ai"
                                                                ? "bg-gradient-to-br from-brand/5 to-brand/10 border-brand/20"
                                                                : "bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700"
                                                        )}
                                                    >
                                                        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1.5">
                                                            <Badge variant={comment.author === "ai" ? "default" : "secondary"} className="text-xs px-1.5 py-0">
                                                                {comment.author}
                                                            </Badge>
                                                            <span>{new Date(comment.created_at).toLocaleString()}</span>
                                                        </div>
                                                        <p className="leading-relaxed">{comment.content}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="text-center py-20 text-muted-foreground">
                                <Bug className="w-12 h-12 mx-auto mb-3 opacity-30" />
                                <p className="text-sm">Select a bug to view details</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Image Modal */}
            {imageModalOpen && selectedBug?.screenshot_path && (
                <div
                    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-8"
                    onClick={() => setImageModalOpen(false)}
                >
                    <img
                        src={`${BUGBASE_API_URL}/api/screenshots/${selectedBug.screenshot_path.split('/').pop()}`}
                        alt="Bug screenshot full size"
                        className="max-w-full max-h-full object-contain rounded-xl shadow-2xl"
                    />
                </div>
            )}
        </div>
    );
}
