// Copyright (c) 2025 Galaxy Technology Service
// BugBase API - Report submission endpoint

import { NextRequest, NextResponse } from "next/server";

const BUGBASE_MCP_URL = process.env.BUGBASE_MCP_URL || "http://localhost:8082";

interface BugReportPayload {
    title: string;
    description?: string;
    severity: "low" | "medium" | "high" | "critical";
    screenshot?: string | null;
    navigationHistory: Array<{
        id: string;
        path: string;
        timestamp: number;
        action: string;
        metadata?: Record<string, unknown>;
    }>;
    pageUrl: string;
    userAgent: string;
}

export async function POST(request: NextRequest) {
    try {
        const body: BugReportPayload = await request.json();

        // Validate required fields
        if (!body.title?.trim()) {
            return NextResponse.json(
                { success: false, message: "Title is required" },
                { status: 400 }
            );
        }

        // Forward to BugBase MCP Server
        const response = await fetch(`${BUGBASE_MCP_URL}/api/bugs`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                title: body.title.trim(),
                description: body.description?.trim() || null,
                severity: body.severity || "medium",
                screenshot_base64: body.screenshot || null,
                navigation_history: body.navigationHistory || [],
                page_url: body.pageUrl || null,
                user_agent: body.userAgent || null,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error("[BugBase API] MCP Server error:", errorData);
            return NextResponse.json(
                { success: false, message: errorData.detail || "Failed to submit bug report" },
                { status: response.status }
            );
        }

        const data = await response.json();

        return NextResponse.json({
            success: true,
            bugId: data.id,
            message: "Bug report submitted successfully",
        });
    } catch (error) {
        console.error("[BugBase API] Error:", error);
        return NextResponse.json(
            { success: false, message: "Internal server error" },
            { status: 500 }
        );
    }
}
