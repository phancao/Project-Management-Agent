'use client';

import { useState } from 'react';
import { format } from 'date-fns';
import { CalendarIcon, Plus, Trash2, Calendar, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

import { Button } from '~/components/ui/button';
import { Input } from '~/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Calendar as CalendarPicker } from '~/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '~/components/ui/popover';
import { useHolidays, type Holiday } from '~/contexts/holidays-context';
import { cn } from '~/lib/utils';

export default function HolidaysSettingsPage() {
    const { holidays, addHoliday, removeHoliday, isLoading } = useHolidays();

    // Form state
    const [newHolidayName, setNewHolidayName] = useState('');
    const [newHolidayDate, setNewHolidayDate] = useState<Date>();
    const [datePickerOpen, setDatePickerOpen] = useState(false);

    const handleAddHoliday = () => {
        if (newHolidayName.trim() && newHolidayDate) {
            addHoliday({
                name: newHolidayName.trim(),
                date: newHolidayDate
            });
            setNewHolidayName('');
            setNewHolidayDate(undefined);
        }
    };

    // Sort holidays by date
    const sortedHolidays = [...holidays].sort((a, b) =>
        a.date.getTime() - b.date.getTime()
    );

    if (isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-indigo-600" />
            </div>
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
                                placeholder="Holiday name (e.g., New Year's Day)"
                                value={newHolidayName}
                                onChange={(e) => setNewHolidayName(e.target.value)}
                                className="flex-1"
                            />
                            <Popover open={datePickerOpen} onOpenChange={setDatePickerOpen}>
                                <PopoverTrigger asChild>
                                    <Button
                                        variant="outline"
                                        className={cn(
                                            "w-[200px] justify-start text-left font-normal",
                                            !newHolidayDate && "text-muted-foreground"
                                        )}
                                    >
                                        <CalendarIcon className="mr-2 h-4 w-4" />
                                        {newHolidayDate ? format(newHolidayDate, "PPP") : "Pick a date"}
                                    </Button>
                                </PopoverTrigger>
                                <PopoverContent className="w-auto p-0" align="start">
                                    <CalendarPicker
                                        mode="single"
                                        selected={newHolidayDate}
                                        onSelect={(date) => {
                                            setNewHolidayDate(date);
                                            setDatePickerOpen(false);
                                        }}
                                        initialFocus
                                    />
                                </PopoverContent>
                            </Popover>
                            <Button
                                onClick={handleAddHoliday}
                                disabled={!newHolidayName.trim() || !newHolidayDate}
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
                                        key={`${holiday.date.toISOString()}-${holiday.name}`}
                                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg group hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="w-16 text-center">
                                                <div className="text-2xl font-bold text-indigo-600">
                                                    {format(holiday.date, 'd')}
                                                </div>
                                                <div className="text-xs text-muted-foreground uppercase">
                                                    {format(holiday.date, 'MMM')}
                                                </div>
                                            </div>
                                            <div>
                                                <div className="font-medium">{holiday.name}</div>
                                                <div className="text-sm text-muted-foreground">
                                                    {format(holiday.date, 'EEEE, MMMM d, yyyy')}
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
                                                    h.date.toISOString() === holiday.date.toISOString() &&
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
                                    <li>Holidays are shared across all projects and teams</li>
                                    <li>Holiday dates are excluded from capacity calculations</li>
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
