"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { cn } from "~/lib/utils";
import { useThemeColors } from "~/core/hooks/use-theme-colors";

interface PageHeaderProps {
    /** Page title */
    title: string;
    /** Page subtitle/description */
    subtitle?: string;
    /** Icon component to display */
    icon?: React.ReactNode;
    /** Back link URL */
    backUrl?: string;
    /** Additional action buttons */
    actions?: React.ReactNode;
    /** Whether to use gradient background */
    gradient?: boolean;
    /** Custom className */
    className?: string;
}

/**
 * Consistent page header component following Galaxy AI Design System
 */
export function PageHeader({
    title,
    subtitle,
    icon,
    backUrl,
    actions,
    gradient = false,
    className,
}: PageHeaderProps) {
    const { accent } = useThemeColors();

    return (
        <header className={cn(
            "border-b",
            gradient
                ? `bg-gradient-to-r ${accent.gradient} border-transparent`
                : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800",
            className
        )}>
            <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <div className="h-16 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 min-w-0">
                        {/* Back button */}
                        {backUrl && (
                            <Link
                                href={backUrl}
                                className={cn(
                                    "p-2 -ml-2 rounded-lg transition-colors shrink-0",
                                    gradient
                                        ? "text-white/80 hover:text-white hover:bg-white/10"
                                        : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
                                )}
                            >
                                <ArrowLeft className="w-5 h-5" />
                            </Link>
                        )}

                        {/* Icon */}
                        {icon && (
                            <div className={cn(
                                "p-2 rounded-lg shrink-0",
                                gradient
                                    ? "bg-white/10"
                                    : `${accent.badgeBg}`
                            )}>
                                <div className={cn(
                                    "w-5 h-5",
                                    gradient
                                        ? "text-white"
                                        : `${accent.text} ${accent.textDark}`
                                )}>
                                    {icon}
                                </div>
                            </div>
                        )}

                        {/* Title & Subtitle */}
                        <div className="min-w-0">
                            <h1 className={cn(
                                "text-lg sm:text-xl font-semibold truncate",
                                gradient ? "text-white" : "text-gray-900 dark:text-white"
                            )}>
                                {title}
                            </h1>
                            {subtitle && (
                                <p className={cn(
                                    "text-sm truncate",
                                    gradient ? "text-white/80" : "text-gray-500 dark:text-gray-400"
                                )}>
                                    {subtitle}
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Actions */}
                    {actions && (
                        <div className="flex items-center gap-2 shrink-0">
                            {actions}
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}

/**
 * Container for page content with consistent padding and max-width
 */
export function PageContent({
    children,
    className,
}: {
    children: React.ReactNode;
    className?: string;
}) {
    return (
        <main className={cn(
            "container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 sm:py-8",
            className
        )}>
            {children}
        </main>
    );
}

/**
 * Full page layout wrapper with consistent background
 */
export function PageLayout({
    children,
    className,
}: {
    children: React.ReactNode;
    className?: string;
}) {
    return (
        <div className={cn(
            "min-h-screen bg-gray-50 dark:bg-gray-950",
            className
        )}>
            {children}
        </div>
    );
}
