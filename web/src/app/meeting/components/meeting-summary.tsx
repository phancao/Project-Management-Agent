'use client';

import { useState, useEffect } from 'react';

interface MeetingSummaryData {
    meetingId: string;
    title: string;
    executiveSummary: string;
    keyPoints: string[];
    topics: string[];
    participantContributions: Record<string, string[]>;
    sentiment: 'positive' | 'neutral' | 'negative';
    actionItemsCount: number;
    decisionsCount: number;
    followUpsCount: number;
}

interface MeetingSummaryProps {
    meetingId: string;
}

export default function MeetingSummary({ meetingId }: MeetingSummaryProps) {
    const [summary, setSummary] = useState<MeetingSummaryData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchSummary();
    }, [meetingId]);

    const fetchSummary = async () => {
        try {
            setLoading(true);
            const res = await fetch(`/api/meetings/${meetingId}/summary`);
            if (!res.ok) throw new Error('Failed to fetch summary');
            const data = await res.json();
            setSummary(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    const getSentimentIcon = (sentiment: string) => {
        switch (sentiment) {
            case 'positive': return '😊';
            case 'negative': return '😟';
            default: return '😐';
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-purple-500 border-t-transparent" />
            </div>
        );
    }

    if (error || !summary) {
        return (
            <div className="text-center py-12">
                <div className="text-4xl mb-4">❌</div>
                <p className="text-red-400">{error || 'Summary not found'}</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-white">{summary.title}</h2>
                <span className="text-2xl" title={`Sentiment: ${summary.sentiment}`}>
                    {getSentimentIcon(summary.sentiment)}
                </span>
            </div>

            {/* Executive Summary */}
            <div className="p-5 bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-xl border border-purple-500/30">
                <h3 className="text-sm font-medium text-purple-300 mb-2">EXECUTIVE SUMMARY</h3>
                <p className="text-white text-lg">{summary.executiveSummary}</p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                    { label: 'Action Items', value: summary.actionItemsCount, icon: '✅', color: 'green' },
                    { label: 'Decisions', value: summary.decisionsCount, icon: '🎯', color: 'blue' },
                    { label: 'Follow-ups', value: summary.followUpsCount, icon: '📌', color: 'yellow' },
                ].map((stat) => (
                    <div
                        key={stat.label}
                        className={`p-4 bg-slate-800/40 rounded-xl border border-slate-700 text-center`}
                    >
                        <div className="text-3xl mb-1">{stat.icon}</div>
                        <div className="text-2xl font-bold text-white">{stat.value}</div>
                        <div className="text-sm text-slate-400">{stat.label}</div>
                    </div>
                ))}
            </div>

            {/* Key Points */}
            <div className="bg-slate-700/30 rounded-xl p-5">
                <h3 className="text-lg font-medium text-white mb-4">📋 Key Points</h3>
                <ul className="space-y-2">
                    {summary.keyPoints.map((point, index) => (
                        <li key={index} className="flex items-start">
                            <span className="text-purple-400 mr-3">•</span>
                            <span className="text-slate-300">{point}</span>
                        </li>
                    ))}
                </ul>
            </div>

            {/* Topics */}
            <div className="bg-slate-700/30 rounded-xl p-5">
                <h3 className="text-lg font-medium text-white mb-4">🏷️ Topics Discussed</h3>
                <div className="flex flex-wrap gap-2">
                    {summary.topics.map((topic, index) => (
                        <span
                            key={index}
                            className="px-3 py-1 bg-slate-600/50 text-slate-300 rounded-full text-sm"
                        >
                            {topic}
                        </span>
                    ))}
                </div>
            </div>

            {/* Participant Contributions */}
            {Object.keys(summary.participantContributions).length > 0 && (
                <div className="bg-slate-700/30 rounded-xl p-5">
                    <h3 className="text-lg font-medium text-white mb-4">👥 Participant Contributions</h3>
                    <div className="space-y-4">
                        {Object.entries(summary.participantContributions).map(([name, contributions]) => (
                            <div key={name} className="border-l-2 border-purple-500 pl-4">
                                <h4 className="font-medium text-white mb-2">{name}</h4>
                                <ul className="space-y-1">
                                    {contributions.map((contrib, index) => (
                                        <li key={index} className="text-slate-400 text-sm">• {contrib}</li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
