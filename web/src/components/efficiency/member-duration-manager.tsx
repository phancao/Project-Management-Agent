import { useState, useEffect } from 'react';
import { format, parse, isValid } from 'date-fns';
import { Calendar as CalendarIcon, Plus, X, Percent, PartyPopper, TreePalm } from "lucide-react";
import type { DateRange } from 'react-day-picker';

import { cn } from "~/lib/utils";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Calendar } from "~/components/ui/calendar";
import { Input } from "~/components/ui/input";
import { Checkbox } from "~/components/ui/checkbox";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { type PMUser } from '~/core/api/pm/users';

export interface Holiday {
    date: Date;
    name: string;
}

export interface MemberPeriod {
    range: DateRange;
    allocation: number; // 0-100
    vacations?: DateRange[]; // Individual vacation dates within this period
}

interface MemberDurationManagerProps {
    members: PMUser[];
    activePeriods: Record<string, MemberPeriod[]>;
    onChange: (periods: Record<string, MemberPeriod[]>) => void;
    holidays?: Holiday[];
    onHolidaysChange?: (holidays: Holiday[]) => void;
}

export function MemberDurationManager({ members, activePeriods, onChange, holidays = [], onHolidaysChange }: MemberDurationManagerProps) {
    const [selectedMember, setSelectedMember] = useState<string | null>(null);
    const [tempDateRange, setTempDateRange] = useState<DateRange | undefined>(undefined);

    // Holiday input state
    const [holidayDate, setHolidayDate] = useState<Date | undefined>(undefined);
    const [holidayName, setHolidayName] = useState("");
    const [showHolidayPopover, setShowHolidayPopover] = useState(false);

    // Vacation input state (per member period)
    const [vacationMember, setVacationMember] = useState<string | null>(null);
    const [vacationPeriodIndex, setVacationPeriodIndex] = useState<number | null>(null);
    const [vacationRange, setVacationRange] = useState<DateRange | undefined>(undefined);

    // Manual Input State
    const [startInput, setStartInput] = useState("");
    const [endInput, setEndInput] = useState("");
    const [allocationInput, setAllocationInput] = useState("100");
    const [isVacationPeriod, setIsVacationPeriod] = useState(false);

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

        // If vacation is checked, we add this as a vacation period with 0% allocation
        if (isVacationPeriod) {
            const currentPeriods = activePeriods[memberId] || [];

            // Find if there's an existing period that encompasses this vacation
            // If not, we still add the vacation as a standalone period with 0% allocation
            const newPeriod: MemberPeriod = {
                range: tempDateRange,
                allocation: 0, // Vacation = 0 capacity
                vacations: [tempDateRange] // Also store it as a vacation for styling
            };

            const newPeriods = [...currentPeriods, newPeriod];

            onChange({
                ...activePeriods,
                [memberId]: newPeriods
            });
        } else {
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
        }

        setTempDateRange(undefined);
        setStartInput("");
        setEndInput("");
        setAllocationInput("100");
        setIsVacationPeriod(false);
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

    // Holiday handlers
    const handleAddHoliday = () => {
        if (!holidayDate || !holidayName.trim() || !onHolidaysChange) return;

        const newHoliday: Holiday = { date: holidayDate, name: holidayName.trim() };
        onHolidaysChange([...holidays, newHoliday]);

        setHolidayDate(undefined);
        setHolidayName("");
        setShowHolidayPopover(false);
    };

    const handleRemoveHoliday = (index: number) => {
        if (!onHolidaysChange) return;
        onHolidaysChange(holidays.filter((_, i) => i !== index));
    };

    // Vacation handlers
    const handleAddVacation = () => {
        if (!vacationRange?.from || vacationMember === null || vacationPeriodIndex === null) return;

        const memberPeriods = activePeriods[vacationMember] || [];
        const updatedPeriods = memberPeriods.map((period, idx) => {
            if (idx === vacationPeriodIndex) {
                return {
                    ...period,
                    vacations: [...(period.vacations || []), vacationRange]
                };
            }
            return period;
        });

        onChange({
            ...activePeriods,
            [vacationMember]: updatedPeriods
        });

        setVacationRange(undefined);
        setVacationMember(null);
        setVacationPeriodIndex(null);
    };

    const handleRemoveVacation = (memberId: string, periodIndex: number, vacationIndex: number) => {
        const memberPeriods = activePeriods[memberId] || [];
        const updatedPeriods = memberPeriods.map((period, idx) => {
            if (idx === periodIndex) {
                return {
                    ...period,
                    vacations: (period.vacations || []).filter((_, i) => i !== vacationIndex)
                };
            }
            return period;
        });

        onChange({
            ...activePeriods,
            [memberId]: updatedPeriods
        });
    };

    return (
        <div className="space-y-4">
            {/* Holidays Section */}
            {onHolidaysChange && (
                <div className="rounded-md border border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/30 p-4">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <PartyPopper className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                            <span className="font-medium text-sm text-amber-800 dark:text-amber-200">Holidays</span>
                            <span className="text-xs text-amber-600 dark:text-amber-400">(applies to all members)</span>
                        </div>
                        <Popover open={showHolidayPopover} onOpenChange={setShowHolidayPopover}>
                            <PopoverTrigger asChild>
                                <Button variant="outline" size="sm" className="h-7 text-xs border-amber-300 dark:border-amber-700">
                                    <Plus className="w-3 h-3 mr-1" /> Add Holiday
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent className="w-auto p-4" align="end">
                                <div className="space-y-3">
                                    <div>
                                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">Date</label>
                                        <Calendar
                                            mode="single"
                                            selected={holidayDate}
                                            onSelect={setHolidayDate}
                                            className="rounded-md border"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">Name</label>
                                        <Input
                                            placeholder="e.g., New Year"
                                            value={holidayName}
                                            onChange={(e) => setHolidayName(e.target.value)}
                                            className="h-8"
                                        />
                                    </div>
                                    <Button
                                        size="sm"
                                        onClick={handleAddHoliday}
                                        disabled={!holidayDate || !holidayName.trim()}
                                        className="w-full"
                                    >
                                        Add Holiday
                                    </Button>
                                </div>
                            </PopoverContent>
                        </Popover>
                    </div>
                    {holidays.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                            {holidays.map((holiday, idx) => (
                                <Badge key={idx} variant="secondary" className="bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-200 border-amber-200 dark:border-amber-700">
                                    <PartyPopper className="w-3 h-3 mr-1" />
                                    {format(holiday.date, "MMM d")} - {holiday.name}
                                    <button onClick={() => handleRemoveHoliday(idx)} className="ml-1.5 hover:text-red-500">
                                        <X className="w-3 h-3" />
                                    </button>
                                </Badge>
                            ))}
                        </div>
                    ) : (
                        <span className="text-xs text-amber-600/70 dark:text-amber-400/70 italic">No holidays defined</span>
                    )}
                </div>
            )}

            {/* Members Section */}
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
                                        <div key={index} className="flex flex-col gap-1">
                                            <div
                                                className="relative flex items-center gap-1.5 py-1 pr-1.5 pl-2 rounded-md overflow-hidden bg-gray-300 dark:bg-gray-700"
                                            >
                                                {/* Progress bar fill as background */}
                                                <div
                                                    className="absolute inset-0 bg-indigo-500 dark:bg-indigo-600 transition-all duration-300"
                                                    style={{ width: `${period.allocation}%` }}
                                                />
                                                {/* Content on top */}
                                                <CalendarIcon className="relative w-3 h-3 text-white/80" />
                                                <span className="relative text-sm text-white font-medium">
                                                    {format(period.range.from!, "MMM d")} - {period.range.to ? format(period.range.to, "MMM d") : "..."}
                                                </span>
                                                <span className="relative ml-1 text-xs font-bold text-white">
                                                    {period.allocation}%
                                                </span>
                                                {/* Vacation button */}
                                                <Popover
                                                    open={vacationMember === member.id && vacationPeriodIndex === index}
                                                    onOpenChange={(open) => {
                                                        if (open) {
                                                            setVacationMember(member.id);
                                                            setVacationPeriodIndex(index);
                                                        } else {
                                                            setVacationMember(null);
                                                            setVacationPeriodIndex(null);
                                                            setVacationRange(undefined);
                                                        }
                                                    }}
                                                >
                                                    <PopoverTrigger asChild>
                                                        <button className="relative ml-1.5 hover:bg-white/20 rounded p-0.5 transition-colors" title="Add vacation">
                                                            <TreePalm className="w-4 h-4 text-emerald-300 hover:text-emerald-200" />
                                                        </button>
                                                    </PopoverTrigger>
                                                    <PopoverContent className="w-auto p-3" align="start">
                                                        <div className="space-y-2">
                                                            <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Add Vacation</label>
                                                            <Calendar
                                                                mode="range"
                                                                selected={vacationRange}
                                                                onSelect={setVacationRange}
                                                                className="rounded-md border"
                                                            />
                                                            <Button
                                                                size="sm"
                                                                onClick={handleAddVacation}
                                                                disabled={!vacationRange?.from}
                                                                className="w-full"
                                                            >
                                                                <TreePalm className="w-3 h-3 mr-1" /> Add Vacation
                                                            </Button>
                                                        </div>
                                                    </PopoverContent>
                                                </Popover>
                                                <button
                                                    onClick={() => handleRemovePeriod(member.id, index)}
                                                    className="relative ml-1 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-full p-0.5 transition-colors"
                                                >
                                                    <X className="w-3 h-3 text-gray-500 hover:text-red-500" />
                                                </button>
                                            </div>
                                            {/* Vacations under this period */}
                                            {period.vacations && period.vacations.length > 0 && (
                                                <div className="flex flex-wrap gap-1 ml-4">
                                                    {period.vacations.map((vacation, vacIdx) => (
                                                        <Badge key={vacIdx} variant="outline" className="text-xs py-0 px-1.5 bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300">
                                                            <TreePalm className="w-2.5 h-2.5 mr-1" />
                                                            {format(vacation.from!, "MMM d")}{vacation.to && vacation.to !== vacation.from ? ` - ${format(vacation.to, "MMM d")}` : ""}
                                                            <button onClick={() => handleRemoveVacation(member.id, index, vacIdx)} className="ml-1 hover:text-red-500">
                                                                <X className="w-2.5 h-2.5" />
                                                            </button>
                                                        </Badge>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
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
                                                    <h4 className="font-medium leading-none">{isVacationPeriod ? 'Add Vacation' : 'Select Active Period'}</h4>
                                                    <Button
                                                        size="sm"
                                                        className="h-7 text-xs"
                                                        disabled={!tempDateRange?.from}
                                                        onClick={() => handleAddPeriod(member.id)}
                                                    >
                                                        Confirm
                                                    </Button>
                                                </div>
                                                {/* Vacation Checkbox */}
                                                <div className="flex items-center gap-2">
                                                    <Checkbox
                                                        id={`vacation-${member.id}`}
                                                        checked={isVacationPeriod}
                                                        onCheckedChange={(checked) => setIsVacationPeriod(checked === true)}
                                                    />
                                                    <label
                                                        htmlFor={`vacation-${member.id}`}
                                                        className="text-sm text-emerald-600 dark:text-emerald-400 cursor-pointer flex items-center gap-1"
                                                    >
                                                        <TreePalm className="w-4 h-4" /> This is a vacation
                                                    </label>
                                                </div>
                                                {/* Allocation - hide when vacation */}
                                                {!isVacationPeriod && (
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
                                                )}
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
