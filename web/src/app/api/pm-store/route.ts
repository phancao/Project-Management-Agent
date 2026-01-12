import { NextResponse } from "next/server";

// This simulates a remote JSON manifest.
// In a real scenario, this could be fetched from an external CMS or S3 bucket.
const PLUGIN_MANIFEST = [
    {
        id: "team-velocity",
        type: "page",
        meta: {
            title: "Velocity",
            description: "Analyze team velocity over time (Completed vs Committed).",
            category: "Analytics",
            icon: "TrendingUp",
            author: "System",
            version: "1.1.0",
        },
    },
    {
        id: "burndown-chart",
        type: "page",
        meta: {
            title: "Burndown",
            description: "Track remaining work against time.",
            category: "Analytics",
            icon: "LineChart",
            author: "System",
            version: "1.0.0",
        },
    },
    {
        id: "sprint-report",
        type: "page",
        meta: {
            title: "Sprint Report",
            description: "Performance summary of the current or past sprints.",
            category: "Analytics",
            icon: "FileText",
            author: "System",
            version: "1.0.0",
        },
    },
    {
        id: "cfd-chart",
        type: "page",
        meta: {
            title: "CFD",
            description: "Cumulative Flow Diagram to visualize workflow stability.",
            category: "Analytics",
            icon: "BarChart2",
            author: "System",
            version: "1.0.0",
        },
    },
    {
        id: "cycle-time",
        type: "page",
        meta: {
            title: "Cycle Time",
            description: "Analyze the time taken to complete tasks.",
            category: "Analytics",
            icon: "Clock",
            author: "System",
            version: "1.0.0",
        },
    },
    {
        id: "work-distribution",
        type: "page",
        meta: {
            title: "Project Resource Distribution",
            description: "Work distribution by type, assignee, or priority.",
            category: "Analytics",
            icon: "PieChart",
            author: "System",
            version: "1.0.0",
        },
    },
    {
        id: "issue-trend",
        type: "page",
        meta: {
            title: "Trend",
            description: "Trend of issues created vs resolved over time.",
            category: "Analytics",
            icon: "TrendingUp",
            author: "System",
            version: "1.0.0",
        },
    },
    {
        id: "worklogs",
        type: "page",
        meta: {
            title: "Worklogs",
            description: "Detailed log of time spent on tasks.",
            category: "Analytics",
            icon: "Clock",
            author: "System",
            version: "1.0.0",
        },
    },
    {
        id: "timeline-view",
        type: "page",
        meta: {
            title: "Timeline",
            description: "Gantt-style view of project roadmap and dependencies.",
            category: "Planning",
            icon: "Calendar",
            author: "System",
            version: "1.0.0",
        },
    },
    {
        id: "efficiency-view",
        type: "page",
        meta: {
            title: "Project Resource Efficiency (EE)",
            shortTitle: "PM Efficiency (EE)",
            description: "Track time usage, focus hours, and meeting load.",
            category: "Analytics",
            icon: "Timer",
            author: "System",
            version: "1.0.0",
        },
    },
    {
        id: "team-view",
        type: "page",
        meta: {
            title: "Team",
            description: "View member assignments and capacity.",
            category: "Team",
            icon: "Users",
            author: "System",
            version: "1.0.0",
        },
    },
    {
        id: "sprint-health-widget",
        type: "widget",
        meta: {
            title: "Sprint Health",
            description: "Quick glance at current sprint status and timeline.",
            category: "Planning",
            icon: "Activity",
            author: "System",
            version: "1.0.0",
            size: { w: 1, h: 1 },
        },
    },
    {
        id: "member-focus",
        type: "page",
        meta: {
            title: "Member Focus",
            description: "Deep dive into individual member focus time patterns.",
            category: "Team",
            icon: "Users",
            author: "System",
            version: "0.5.0",
        },
    },
];

export async function GET() {
    return NextResponse.json(PLUGIN_MANIFEST);
}
