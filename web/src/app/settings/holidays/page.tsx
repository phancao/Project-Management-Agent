'use client';

import { useState } from 'react';
import { format, differenceInDays } from 'date-fns';
import { CalendarIcon, Plus, Trash2, Calendar, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import type { DateRange } from 'react-day-picker';
import { WorkspaceLoading } from '~/components/ui/workspace-loading';

import { Button } from '~/components/ui/button';
import { Input } from '~/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Calendar as CalendarPicker } from '~/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '~/components/ui/popover';
import { useHolidays } from '~/contexts/holidays-context';
import { cn } from '~/lib/utils';

export default function HolidaysSettingsPage() {
    const { holidays, addHoliday, removeHoliday, isLoading } = useHolidays();

    // Form state
    const [newHolidayName, setNewHolidayName] = useState('');
    const [newHolidayRange, setNewHolidayRange] = useState<DateRange | undefined>();
    const [datePickerOpen, setDatePickerOpen] = useState(false);

    const handleAddHoliday = () => {
        if (newHolidayName.trim() && newHolidayRange?.from) {
            addHoliday({
                name: newHolidayName.trim(),
                range: newHolidayRange
            });
            setNewHolidayName('');
            setNewHolidayRange(undefined);
        }
    };

    // Sort holidays by start date
    const sortedHolidays = [...holidays].sort((a, b) => {
        const aDate = a.range.from || new Date();
        const bDate = b.range.from || new Date();
        return aDate.getTime() - bDate.getTime();
    });

    // Format date range for display
    const formatRange = (range: DateRange): string => {
        if (!range.from) return 'No date';
        if (!range.to || range.from.getTime() === range.to.getTime()) {
            return format(range.from, 'MMM d, yyyy');
        }
        // Same month
        if (range.from.getMonth() === range.to.getMonth() && range.from.getFullYear() === range.to.getFullYear()) {
            return `${format(range.from, 'MMM d')} - ${format(range.to, 'd, yyyy')}`;
        }
        return `${format(range.from, 'MMM d')} - ${format(range.to, 'MMM d, yyyy')}`;
    };

    // Calculate duration
    const getDuration = (range: DateRange): string => {
        if (!range.from) return '';
        const to = range.to || range.from;
        const days = differenceInDays(to, range.from) + 1;
        return days === 1 ? '1 day' : `${days} days`;
    };

    if (isLoading) {
        return (
            <WorkspaceLoading
                title="Loading Holidays"
                subtitle="Fetching holiday data..."
                items={[
                    { label: "Holidays", isLoading: true },
                ]}
                icon={<Calendar className="w-6 h-6 text-white" />}
                height="min-h-screen"
            />
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
            {/* Header */}
            <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
                <div className="container mx-auto max-w-4xl px-4 h-16 flex items-center gap-4">
                    <Link
                        href="/team"
                        className="p-2 -ml-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div className="flex items-center gap-3">
                        <Calendar className="w-6 h-6 text-indigo-600" />
                        <h1 className="text-xl font-semibold">Holidays & Time Off</h1>
                    </div>
                </div>
            </div>

            <main className="container mx-auto max-w-4xl px-4 py-8 space-y-8">
                {/* Add Holiday Card */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Add Holiday</CardTitle>
                        <CardDescription>
                            Add global holidays that apply to all team members. These holidays will be excluded from capacity calculations.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex gap-3">
                            <Input
                                placeholder="Holiday name (e.g., Tet Holiday)"
                                value={newHolidayName}
                                onChange={(e) => setNewHolidayName(e.target.value)}
                                className="flex-1"
                            />
                            <Popover open={datePickerOpen} onOpenChange={setDatePickerOpen}>
                                <PopoverTrigger asChild>
                                    <Button
                                        variant="outline"
                                        className={cn(
                                            "w-[280px] justify-start text-left font-normal",
                                            !newHolidayRange?.from && "text-muted-foreground"
                                        )}
                                    >
                                        <CalendarIcon className="mr-2 h-4 w-4" />
                                        {newHolidayRange?.from ? (
                                            formatRange(newHolidayRange)
                                        ) : (
                                            "Pick date range"
                                        )}
                                    </Button>
                                </PopoverTrigger>
                                <PopoverContent className="w-auto p-0" align="start">
                                    <CalendarPicker
                                        mode="range"
                                        selected={newHolidayRange}
                                        onSelect={setNewHolidayRange}
                                        numberOfMonths={2}
                                        initialFocus
                                    />
                                </PopoverContent>
                            </Popover>
                            <Button
                                onClick={handleAddHoliday}
                                disabled={!newHolidayName.trim() || !newHolidayRange?.from}
                            >
                                <Plus className="w-4 h-4 mr-2" />
                                Add
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Holidays List */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Holidays ({holidays.length})</CardTitle>
                        <CardDescription>
                            Manage your team's holidays. These dates will be excluded from efficiency calculations.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {sortedHolidays.length === 0 ? (
                            <div className="text-center py-8 text-muted-foreground">
                                <Calendar className="w-12 h-12 mx-auto mb-4 opacity-50" />
                                <p>No holidays configured yet.</p>
                                <p className="text-sm mt-1">Add holidays above to exclude them from capacity calculations.</p>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {sortedHolidays.map((holiday, index) => (
                                    <div
                                        key={`${holiday.range.from?.toISOString()}-${holiday.name}`}
                                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg group hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="w-16 text-center">
                                                {holiday.range.from && (
                                                    <>
                                                        <div className="text-2xl font-bold text-indigo-600">
                                                            {format(holiday.range.from, 'd')}
                                                        </div>
                                                        <div className="text-xs text-muted-foreground uppercase">
                                                            {format(holiday.range.from, 'MMM')}
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                            <div>
                                                <div className="font-medium">{holiday.name}</div>
                                                <div className="text-sm text-muted-foreground flex items-center gap-2">
                                                    <span>{formatRange(holiday.range)}</span>
                                                    <span className="text-xs px-1.5 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded">
                                                        {getDuration(holiday.range)}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                                            onClick={() => {
                                                // Find actual index in original array
                                                const actualIndex = holidays.findIndex(h =>
                                                    h.range.from?.toISOString() === holiday.range.from?.toISOString() &&
                                                    h.name === holiday.name
                                                );
                                                if (actualIndex !== -1) {
                                                    removeHoliday(actualIndex);
                                                }
                                            }}
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Info Card */}
                <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/10">
                    <CardContent className="pt-6">
                        <div className="flex gap-3">
                            <CalendarIcon className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
                            <div className="text-sm text-blue-800 dark:text-blue-300">
                                <p className="font-medium mb-1">How holidays work</p>
                                <ul className="list-disc list-inside space-y-1 text-blue-700 dark:text-blue-400">
                                    <li>Holidays can span multiple days (e.g., Tet holiday week)</li>
                                    <li>Holidays are shared across all projects and teams</li>
                                    <li>All dates in the range are excluded from capacity calculations</li>
                                    <li>Members on vacation have a separate tracking system per member</li>
                                </ul>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </main>
        </div>
    );
}
