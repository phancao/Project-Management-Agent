'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Badge } from "~/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar";
import Link from "next/link";
// @ts-expect-error - Direct import
import Check from "lucide-react/dist/esm/icons/check";
// @ts-expect-error - Direct import
import X from "lucide-react/dist/esm/icons/x";
// @ts-expect-error - Direct import
import Clock from "lucide-react/dist/esm/icons/clock";

// Mock Data
const initialEntries = [
    { id: '1', user: 'Alice', user_id: 'alice-id', project: 'Website Redesign', task: 'Homepage Layout', hours: 6.5, date: '2025-05-12', status: 'pending' },
    { id: '2', user: 'Bob', user_id: 'bob-id', project: 'Mobile App', task: 'API Integration', hours: 8.0, date: '2025-05-12', status: 'approved' },
    { id: '3', user: 'Alice', user_id: 'alice-id', project: 'Website Redesign', task: 'Navigation Menu', hours: 2.0, date: '2025-05-13', status: 'rejected' },
    { id: '4', user: 'Charlie', user_id: 'charlie-id', project: 'Website Redesign', task: 'Assets', hours: 4.0, date: '2025-05-12', status: 'approved' },
];

export function TimesheetGrid() {
    const [entries, setEntries] = useState(initialEntries);

    const handleApprove = (id: string) => {
        setEntries(entries.map(e => e.id === id ? { ...e, status: 'approved' } : e));
    };

    const handleReject = (id: string) => {
        setEntries(entries.map(e => e.id === id ? { ...e, status: 'rejected' } : e));
    };

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Time Entries</CardTitle>
                    <CardDescription>Review and approve weekly time logs.</CardDescription>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm">Export CSV</Button>
                </div>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border border-gray-100 dark:border-gray-800">
                    <div className="grid grid-cols-6 gap-4 p-4 font-medium text-sm text-muted-foreground border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50">
                        <div className="col-span-2">User & Task</div>
                        <div>Project</div>
                        <div>Date</div>
                        <div>Hours</div>
                        <div className="text-right">Actions</div>
                    </div>
                    <div className="divide-y divide-gray-100 dark:divide-gray-800">
                        {entries.map((entry) => (
                            <div key={entry.id} className="grid grid-cols-6 gap-4 p-4 items-center hover:bg-gray-50/50 dark:hover:bg-gray-900/50 transition-colors">
                                <div className="col-span-2 flex items-center gap-3">
                                    <Link href={`/team/member/${encodeURIComponent(entry.user_id || entry.user)}?returnTab=worklogs`}>
                                        <Avatar className="w-8 h-8 hover:opacity-80 transition-opacity">
                                            <AvatarFallback>{entry.user[0]}</AvatarFallback>
                                        </Avatar>
                                    </Link>
                                    <div>
                                        <div className="font-medium text-sm">{entry.task}</div>
                                        <div className="text-xs text-muted-foreground">by {entry.user}</div>
                                    </div>
                                </div>
                                <div className="text-sm">
                                    <Badge variant="outline" className="font-normal">{entry.project}</Badge>
                                </div>
                                <div className="text-sm text-muted-foreground">{entry.date}</div>
                                <div className="flex items-center gap-1.5 text-sm font-medium">
                                    <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                                    {entry.hours}h
                                </div>
                                <div className="text-right flex items-center justify-end gap-2">
                                    {entry.status === 'pending' ? (
                                        <>
                                            <Button size="icon" variant="ghost" className="h-8 w-8 text-green-600 hover:text-green-700 hover:bg-green-50" onClick={() => handleApprove(entry.id)}>
                                                <Check className="w-4 h-4" />
                                            </Button>
                                            <Button size="icon" variant="ghost" className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => handleReject(entry.id)}>
                                                <X className="w-4 h-4" />
                                            </Button>
                                        </>
                                    ) : (
                                        <Badge variant={entry.status === 'approved' ? 'default' : 'destructive'} className="capitalize">
                                            {entry.status}
                                        </Badge>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
