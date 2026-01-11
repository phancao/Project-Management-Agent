"use client";

import { cn } from "~/lib/utils";
import { forwardRef } from "react";

/**
 * Color schemes for glow effects
 */
const colorSchemes = {
    indigo: {
        // Container glow
        containerShadow: "shadow-lg dark:shadow-2xl dark:shadow-indigo-500/5",
        // Header gradient
        headerGradient: "from-indigo-50 dark:from-indigo-500/10 via-violet-50/50 dark:via-violet-500/5 to-transparent",
        headerRadial: "from-indigo-100/50 dark:from-indigo-500/10",
        // Icon background
        iconBg: "from-indigo-500 to-violet-600",
        iconShadow: "shadow-indigo-500/30",
        // Item selected state
        itemSelectedBg: "bg-indigo-50 dark:bg-gradient-to-r dark:from-indigo-500/20 dark:to-violet-500/10",
        itemSelectedBorder: "border-indigo-200 dark:border-indigo-500/30",
        itemSelectedShadow: "shadow-lg shadow-indigo-100 dark:shadow-indigo-500/10",
        // Text colors
        textSelected: "text-indigo-900 dark:text-white",
        textAccent: "text-indigo-600 dark:text-indigo-400",
    },
    brand: {
        containerShadow: "shadow-lg dark:shadow-2xl dark:shadow-brand/5",
        headerGradient: "from-brand/10 dark:from-brand/10 via-brand/5 dark:via-brand/5 to-transparent",
        headerRadial: "from-brand/10 dark:from-brand/10",
        iconBg: "from-brand to-brand/80",
        iconShadow: "shadow-brand/30",
        itemSelectedBg: "bg-brand/5 dark:bg-gradient-to-r dark:from-brand/20 dark:to-brand/10",
        itemSelectedBorder: "border-brand/30 dark:border-brand/30",
        itemSelectedShadow: "shadow-lg shadow-brand/10 dark:shadow-brand/10",
        textSelected: "text-brand dark:text-white",
        textAccent: "text-brand dark:text-brand",
    },
    emerald: {
        containerShadow: "shadow-lg dark:shadow-2xl dark:shadow-emerald-500/5",
        headerGradient: "from-emerald-50 dark:from-emerald-500/10 via-teal-50/50 dark:via-teal-500/5 to-transparent",
        headerRadial: "from-emerald-100/50 dark:from-emerald-500/10",
        iconBg: "from-emerald-500 to-teal-600",
        iconShadow: "shadow-emerald-500/30",
        itemSelectedBg: "bg-emerald-50 dark:bg-gradient-to-r dark:from-emerald-500/20 dark:to-teal-500/10",
        itemSelectedBorder: "border-emerald-200 dark:border-emerald-500/30",
        itemSelectedShadow: "shadow-lg shadow-emerald-100 dark:shadow-emerald-500/10",
        textSelected: "text-emerald-900 dark:text-white",
        textAccent: "text-emerald-600 dark:text-emerald-400",
    },
    amber: {
        containerShadow: "shadow-lg dark:shadow-2xl dark:shadow-amber-500/5",
        headerGradient: "from-amber-50 dark:from-amber-500/10 via-orange-50/50 dark:via-orange-500/5 to-transparent",
        headerRadial: "from-amber-100/50 dark:from-amber-500/10",
        iconBg: "from-amber-500 to-orange-600",
        iconShadow: "shadow-amber-500/30",
        itemSelectedBg: "bg-amber-50 dark:bg-gradient-to-r dark:from-amber-500/20 dark:to-orange-500/10",
        itemSelectedBorder: "border-amber-200 dark:border-amber-500/30",
        itemSelectedShadow: "shadow-lg shadow-amber-100 dark:shadow-amber-500/10",
        textSelected: "text-amber-900 dark:text-white",
        textAccent: "text-amber-600 dark:text-amber-400",
    },
};

export type GlowColorScheme = keyof typeof colorSchemes;

interface GlowCardContainerProps extends React.HTMLAttributes<HTMLDivElement> {
    colorScheme?: GlowColorScheme;
}

interface GlowCardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
    colorScheme?: GlowColorScheme;
}

interface GlowCardItemProps extends React.HTMLAttributes<HTMLDivElement> {
    colorScheme?: GlowColorScheme;
    selected?: boolean;
}

interface GlowCardIconProps extends React.HTMLAttributes<HTMLDivElement> {
    colorScheme?: GlowColorScheme;
    size?: "sm" | "md" | "lg";
}

/**
 * GlowCard.Container - Main card wrapper with premium glow shadow
 */
const GlowCardContainer = forwardRef<HTMLDivElement, GlowCardContainerProps>(
    ({ colorScheme = "indigo", className, children, ...props }, ref) => {
        const colors = colorSchemes[colorScheme];
        return (
            <div
                ref={ref}
                className={cn(
                    "bg-card rounded-2xl border border-gray-200 dark:border-0 overflow-hidden",
                    colors.containerShadow,
                    className
                )}
                {...props}
            >
                {children}
            </div>
        );
    }
);
GlowCardContainer.displayName = "GlowCard.Container";

/**
 * GlowCard.Header - Premium gradient header with radial glow overlay
 */
const GlowCardHeader = forwardRef<HTMLDivElement, GlowCardHeaderProps>(
    ({ colorScheme = "indigo", className, children, ...props }, ref) => {
        const colors = colorSchemes[colorScheme];
        return (
            <div
                ref={ref}
                className={cn(
                    "relative p-4 border-b border-gray-100 dark:border-slate-800/50",
                    `bg-gradient-to-r ${colors.headerGradient}`,
                    className
                )}
                {...props}
            >
                {/* Radial glow overlay */}
                <div
                    className={cn(
                        "absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] via-transparent to-transparent",
                        colors.headerRadial
                    )}
                />
                <div className="relative">{children}</div>
            </div>
        );
    }
);
GlowCardHeader.displayName = "GlowCard.Header";

/**
 * GlowCard.Item - Selectable item with glow effect on selection
 */
const GlowCardItem = forwardRef<HTMLDivElement, GlowCardItemProps>(
    ({ colorScheme = "indigo", selected = false, className, children, ...props }, ref) => {
        const colors = colorSchemes[colorScheme];
        return (
            <div
                ref={ref}
                className={cn(
                    "group relative flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all duration-300",
                    selected
                        ? cn(colors.itemSelectedBg, "border", colors.itemSelectedBorder, colors.itemSelectedShadow)
                        : "border border-transparent hover:bg-gray-50 dark:hover:bg-slate-800/50 hover:border-gray-200 dark:hover:border-slate-700/50",
                    className
                )}
                {...props}
            >
                {children}
            </div>
        );
    }
);
GlowCardItem.displayName = "GlowCard.Item";

/**
 * GlowCard.Icon - Gradient icon container with glow shadow
 */
const GlowCardIcon = forwardRef<HTMLDivElement, GlowCardIconProps>(
    ({ colorScheme = "indigo", size = "md", className, children, ...props }, ref) => {
        const colors = colorSchemes[colorScheme];
        const sizeClasses = {
            sm: "w-8 h-8 rounded-lg",
            md: "w-10 h-10 rounded-xl",
            lg: "w-12 h-12 rounded-xl",
        };
        return (
            <div
                ref={ref}
                className={cn(
                    "flex items-center justify-center shadow-lg",
                    `bg-gradient-to-br ${colors.iconBg}`,
                    colors.iconShadow,
                    sizeClasses[size],
                    className
                )}
                {...props}
            >
                {children}
            </div>
        );
    }
);
GlowCardIcon.displayName = "GlowCard.Icon";

/**
 * Get color scheme utilities for custom styling
 */
export function useGlowColors(colorScheme: GlowColorScheme = "indigo") {
    return colorSchemes[colorScheme];
}

/**
 * GlowCard compound component for premium card design
 * 
 * @example
 * ```tsx
 * <GlowCard.Container>
 *   <GlowCard.Header>
 *     <GlowCard.Icon><Users className="w-4 h-4 text-white" /></GlowCard.Icon>
 *     <h3>Title</h3>
 *   </GlowCard.Header>
 *   <div className="p-4">
 *     <GlowCard.Item selected={isSelected}>
 *       Item content
 *     </GlowCard.Item>
 *   </div>
 * </GlowCard.Container>
 * ```
 */
export const GlowCard = {
    Container: GlowCardContainer,
    Header: GlowCardHeader,
    Item: GlowCardItem,
    Icon: GlowCardIcon,
};

export default GlowCard;
