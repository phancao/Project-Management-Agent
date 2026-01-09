import { useState, useEffect } from 'react';
import { format, parse, isValid } from 'date-fns';
import { Calendar as CalendarIcon, Plus, X, Percent } from "lucide-react";
import type { DateRange } from 'react-day-picker';

import { cn } from "~/lib/utils";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Calendar } from "~/components/ui/calendar";
import { Input } from "~/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { type PMUser } from '~/core/api/pm/users';

export interface MemberPeriod {
    range: DateRange;
    allocation: number; // 0-100
}

interface MemberDurationManagerProps {
    members: PMUser[];
    activePeriods: Record<string, MemberPeriod[]>;
    onChange: (periods: Record<string, MemberPeriod[]>) => void;
}

export function MemberDurationManager({ members, activePeriods, onChange }: MemberDurationManagerProps) {
    const [selectedMember, setSelectedMember] = useState<string | null>(null);
    const [tempDateRange, setTempDateRange] = useState<DateRange | undefined>(undefined);

    // Manual Input State
    const [startInput, setStartInput] = useState("");
    const [endInput, setEndInput] = useState("");
    const [allocationInput, setAllocationInput] = useState("100");

    // Sync DateRange -> Inputs (When selected via Calendar)
    useEffect(() => {
        if (tempDateRange?.from) {
            setStartInput(format(tempDateRange.from, "yyyy-MM-dd"));
        } else {
            setStartInput("");
        }
        if (tempDateRange?.to) {
            setEndInput(format(tempDateRange.to, "yyyy-MM-dd"));
        } else {
            setEndInput(""); // Correctly clear end input if range is cleared or single date
        }
    }, [tempDateRange]);

    const handleManualInputChange = (type: 'start' | 'end', value: string) => {
        if (type === 'start') setStartInput(value);
        else setEndInput(value);

        const parsedDate = parse(value, "yyyy-MM-dd", new Date());
        if (isValid(parsedDate)) {
            setTempDateRange(prev => {
                if (type === 'start') {
                    return { ...prev, from: parsedDate };
                } else {
                    return { ...prev, from: prev?.from, to: parsedDate };
                }
            });
        }
    };

    const handleAllocationChange = (value: string) => {
        // Enforce 0-100
        const num = parseInt(value);
        if (isNaN(num)) {
            setAllocationInput(value); // Allow empty/partial
            return;
        }
        if (num >= 0 && num <= 100) {
            setAllocationInput(String(num));
        }
    };

    const handleAddPeriod = (memberId: string) => {
        if (!tempDateRange?.from) return;

        // Default to 100 if invalid
        const allocation = parseInt(allocationInput) || 100;

        const currentPeriods = activePeriods[memberId] || [];
        const newPeriod: MemberPeriod = {
            range: tempDateRange,
            allocation: allocation
        };

        const newPeriods = [...currentPeriods, newPeriod];

        onChange({
            ...activePeriods,
            [memberId]: newPeriods
        });

        setTempDateRange(undefined);
        setStartInput("");
        setEndInput("");
        setAllocationInput("100");
        setSelectedMember(null);
    };

    const handleRemovePeriod = (memberId: string, index: number) => {
        const currentPeriods = activePeriods[memberId] || [];
        const newPeriods = currentPeriods.filter((_, i) => i !== index);

        onChange({
            ...activePeriods,
            [memberId]: newPeriods
        });
    };

    return (
        <div className="space-y-4">
            <div className="rounded-md border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
                <div className="divide-y divide-gray-100 dark:divide-gray-800">
                    {members.map(member => {
                        const periods = activePeriods[member.id] || [];
                        const isAdding = selectedMember === member.id;

                        return (
                            <div key={member.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div className="flex items-center gap-3 min-w-[200px]">
                                    <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-sm font-medium">
                                        {member.name.charAt(0)}
                                    </div>
                                    <span className="font-medium text-sm text-gray-900 dark:text-gray-100">{member.name}</span>
                                </div>

                                <div className="flex-1 flex flex-wrap items-center gap-2">
                                    {periods.length === 0 && !isAdding && (
                                        <span className="text-xs text-gray-400 italic">Full Project Duration (100%)</span>
                                    )}

                                    {periods.map((period, index) => (
                                        <Badge key={index} variant="secondary" className="gap-1.5 py-1 pr-1.5 flex items-center">
                                            <CalendarIcon className="w-3 h-3 text-gray-500" />
                                            <span>
                                                {format(period.range.from!, "MMM d")} - {period.range.to ? format(period.range.to, "MMM d") : "..."}
                                            </span>
                                            {period.allocation !== 100 && (
                                                <span className="ml-1 text-xs font-semibold text-indigo-600 bg-indigo-50 px-1 rounded">
                                                    {period.allocation}%
                                                </span>
                                            )}
                                            <button
                                                onClick={() => handleRemovePeriod(member.id, index)}
                                                className="ml-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full p-0.5 transition-colors"
                                            >
                                                <X className="w-3 h-3 text-gray-500 hover:text-red-500" />
                                            </button>
                                        </Badge>
                                    ))}

                                    <Popover open={isAdding} onOpenChange={(open) => {
                                        if (open) setSelectedMember(member.id);
                                        else {
                                            setSelectedMember(null);
                                            setTempDateRange(undefined);
                                            setStartInput("");
                                            setEndInput("");
                                            setAllocationInput("100");
                                        }
                                    }}>
                                        <PopoverTrigger asChild>
                                            <Button variant="ghost" size="sm" className="h-7 text-xs text-gray-500 gap-1 border border-dashed border-gray-300">
                                                <Plus className="w-3 h-3" />
                                                Add Duration
                                            </Button>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-auto p-0" align="start">
                                            <div className="flex flex-col gap-4 p-4">
                                                <div className="flex justify-between items-center">
                                                    <h4 className="font-medium leading-none">Select Active Period</h4>
                                                    <Button
                                                        size="sm"
                                                        className="h-7 text-xs"
                                                        disabled={!tempDateRange?.from}
                                                        onClick={() => handleAddPeriod(member.id)}
                                                    >
                                                        Confirm
                                                    </Button>
                                                </div>
                                                <div className="grid gap-1.5">
                                                    <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Allocation %</label>
                                                    <div className="relative">
                                                        <Percent className="absolute right-2.5 top-2.5 h-3 w-3 text-muted-foreground" />
                                                        <Input
                                                            className="h-8 text-xs font-mono"
                                                            placeholder="100"
                                                            type="number"
                                                            min="0"
                                                            max="100"
                                                            value={allocationInput}
                                                            onChange={(e) => handleAllocationChange(e.target.value)}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="border-t border-border" />
                                            <div className="flex gap-8 px-3 pt-3">
                                                <div className="grid gap-1.5 flex-1">
                                                    <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Start Date</label>
                                                    <Input
                                                        className="h-8 text-xs font-mono"
                                                        placeholder="YYYY-MM-DD"
                                                        value={startInput}
                                                        onChange={(e) => handleManualInputChange('start', e.target.value)}
                                                    />
                                                </div>
                                                <div className="grid gap-1.5 flex-1">
                                                    <label className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">End Date</label>
                                                    <Input
                                                        className="h-8 text-xs font-mono"
                                                        placeholder="YYYY-MM-DD"
                                                        value={endInput}
                                                        onChange={(e) => handleManualInputChange('end', e.target.value)}
                                                    />
                                                </div>
                                            </div>
                                            <Calendar
                                                initialFocus
                                                mode="range"
                                                defaultMonth={tempDateRange?.from || new Date()}
                                                selected={tempDateRange}
                                                onSelect={setTempDateRange}
                                                numberOfMonths={2}
                                                className="p-3"
                                            />
                                        </PopoverContent>
                                    </Popover>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
