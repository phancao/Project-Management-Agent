
'use client';

import { cn } from "~/lib/utils";

interface DailyWorklogChartProps {
    hours: number;
    target?: number; // Default 8
    size?: number;   // Default 36 (Day View)
    isWeekend?: boolean;
    strokeWidth?: number;
    showText?: boolean;
}

export function DailyWorklogChart({
    hours,
    target = 8,
    size = 36,
    isWeekend = false,
    strokeWidth = 4,
    showText = true
}: DailyWorklogChartProps) {
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    // Visual percentage for the stroke (capped/min at 100)
    const percentage = target > 0 ? Math.min((hours / target) * 100, 100) : 0;
    // Raw percentage for status color (can exceed 100)
    const rawPercentage = target > 0 ? (hours / target) * 100 : 0;

    // Status Logic
    const getStatusColor = () => {
        if (hours === 0) return 'fill-transparent';
        if (rawPercentage < 50) return 'fill-red-500'; // Severe under-performance (< 50%)
        if (rawPercentage >= 90) return 'fill-emerald-500'; // Green for >= 90%
        return 'fill-amber-400'; // Moderate under-performance (50-90%)
    };

    return (
        <div className="relative flex items-center justify-center">
            <svg width={size} height={size} className="transform -rotate-90">
                {/* Background circle (outline) */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius - 2}
                    fill="none"
                    strokeWidth={2}
                    className="stroke-gray-300 dark:stroke-gray-600"
                />

                {/* Visual Wedge/Circle Logic */}
                {hours > 0 && (() => {
                    const hoursAngle = Math.min((hours / target) * 360, 360);
                    const endAngle = hoursAngle;
                    const largeArc = endAngle > 180 ? 1 : 0;
                    const cx = size / 2;
                    const cy = size / 2;
                    const r = radius - 4;

                    // Full Circle
                    if (hours >= target) {
                        return (
                            <circle
                                cx={cx}
                                cy={cy}
                                r={r}
                                className={cn(
                                    "transition-all duration-500",
                                    getStatusColor()
                                )}
                            />
                        );
                    }

                    // Partial Wedge
                    const x1 = cx;
                    const y1 = cy - r;
                    const x2 = cx + r * Math.sin((endAngle * Math.PI) / 180);
                    const y2 = cy - r * Math.cos((endAngle * Math.PI) / 180);

                    return (
                        <path
                            d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`}
                            className={cn(
                                "transition-all duration-500",
                                getStatusColor()
                            )}
                        />
                    );
                })()}

                {/* Clock tick marks (8 ticks for 8 hours) */}
                {[...Array(8)].map((_, i) => {
                    const angle = (i / 8) * 360;
                    const tickOuterRadius = size / 2 - 1;
                    const tickInnerRadius = tickOuterRadius - 5;
                    const x1 = size / 2 + tickInnerRadius * Math.cos((angle * Math.PI) / 180);
                    const y1 = size / 2 + tickInnerRadius * Math.sin((angle * Math.PI) / 180);
                    const x2 = size / 2 + tickOuterRadius * Math.cos((angle * Math.PI) / 180);
                    const y2 = size / 2 + tickOuterRadius * Math.sin((angle * Math.PI) / 180);
                    return (
                        <line
                            key={i}
                            x1={x1}
                            y1={y1}
                            x2={x2}
                            y2={y2}
                            strokeWidth={1.5}
                            className="stroke-gray-600 dark:stroke-gray-400"
                        />
                    );
                })}
            </svg>

            {showText && (
                <span className={cn(
                    "absolute inset-0 flex items-center justify-center text-[10px] font-bold",
                    hours === 0 && !isWeekend ? "text-red-500" : "text-gray-700 dark:text-gray-200"
                )}>
                    {Number.isInteger(hours) ? hours : hours.toFixed(1)}
                </span>
            )}
        </div>
    );
}
