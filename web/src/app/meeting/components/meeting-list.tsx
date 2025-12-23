'use client';

import { useState, useEffect } from 'react';

interface Meeting {
    id: string;
    title: string;
    status: 'pending' | 'completed' | 'failed';
    createdAt: string;
    participantsCount: number;
    actionItemsCount?: number;
}

interface MeetingListProps {
    onSelectMeeting: (meetingId: string) => void;
    projectId?: string | null;
}

export default function MeetingList({ onSelectMeeting, projectId }: MeetingListProps) {
    const [meetings, setMeetings] = useState<Meeting[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'completed' | 'pending'>('all');

    useEffect(() => {
        fetchMeetings();
    }, [projectId]);

    const fetchMeetings = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (projectId) {
                params.append('projectId', projectId);
            }

            const res = await fetch(`/api/meetings?${params.toString()}`);
            if (res.ok) {
                const data = await res.json();
                setMeetings(data.meetings || []);
            }
        } catch (err) {
            console.error('Failed to fetch meetings:', err);
        } finally {
            setLoading(false);
        }
    };

    const filteredMeetings = meetings.filter((m) =>
        filter === 'all' ? true : m.status === filter
    );

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return 'bg-green-500/20 text-green-400';
            case 'pending': return 'bg-yellow-500/20 text-yellow-400';
            case 'failed': return 'bg-red-500/20 text-red-400';
            default: return 'bg-slate-500/20 text-slate-400';
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-purple-500 border-t-transparent" />
            </div>
        );
    }

    return (
        <div>
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
                <h2 className="text-2xl font-bold text-white">All Meetings</h2>

                {/* Filter */}
                <div className="flex flex-wrap gap-2">
                    {['all', 'completed', 'pending'].map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f as any)}
                            className={`
                px-4 py-2 rounded-lg text-sm font-medium transition-colors
                ${filter === f
                                    ? 'bg-purple-600 text-white'
                                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                                }
              `}
                        >
                            {f.charAt(0).toUpperCase() + f.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            {filteredMeetings.length === 0 ? (
                <div className="text-center py-12">
                    <div className="text-4xl mb-4">📭</div>
                    <p className="text-slate-400">No meetings found</p>
                    <p className="text-slate-500 text-sm mt-1">
                        {projectId ? "Upload a recording for this project" : "Upload a recording to get started"}
                    </p>
                </div>
            ) : (
                <div className="space-y-3">
                    {filteredMeetings.map((meeting) => (
                        <div
                            key={meeting.id}
                            onClick={() => meeting.status === 'completed' && onSelectMeeting(meeting.id)}
                            className={`
                p-4 bg-slate-700/30 rounded-xl border border-slate-600/50
                ${meeting.status === 'completed'
                                    ? 'cursor-pointer hover:bg-slate-700/50 hover:border-purple-500/50'
                                    : 'opacity-70'
                                }
                transition-all duration-200
              `}
                        >
                            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center flex-wrap gap-3">
                                        <h3 className="text-lg font-medium text-white truncate">{meeting.title}</h3>
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(meeting.status)}`}>
                                            {meeting.status}
                                        </span>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-sm text-slate-400">
                                        <span>📅 {formatDate(meeting.createdAt)}</span>
                                        <span>👥 {meeting.participantsCount} participants</span>
                                        {meeting.actionItemsCount !== undefined && (
                                            <span>✅ {meeting.actionItemsCount} action items</span>
                                        )}
                                    </div>
                                </div>

                                {meeting.status === 'completed' && (
                                    <button className="w-full sm:w-auto px-4 py-2 bg-purple-600/20 text-purple-400 rounded-lg hover:bg-purple-600/30 transition-colors text-sm">
                                        View Details →
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
