'use client';

import { useState, Suspense } from 'react';
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MeetingUpload from './components/meeting-upload';
import MeetingList from './components/meeting-list';
import MeetingSummary from './components/meeting-summary';
import ActionItemsView from './components/action-items-view';
import { PMHeader } from "../pm/components/pm-header";
import { PMLoadingProvider } from "../pm/context/pm-loading-context";
import { PMLoadingManager } from "../pm/components/pm-loading-manager";

// Create a client
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1,
        },
    },
});

function MeetingPageContent() {
    const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'upload' | 'list' | 'summary' | 'actions'>('upload');

    return (
        <QueryClientProvider client={queryClient}>
            <PMLoadingProvider>
                <PMLoadingManager />
                <PMHeader />
                <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 pt-20 pb-12">
                    <div className="container mx-auto px-4">
                        {/* Header */}
                        <div className="mb-8">
                            <h1 className="text-3xl sm:text-4xl font-bold text-white mb-2">
                                Meeting Notes Agent
                            </h1>
                            <p className="text-slate-300 text-sm sm:text-base max-w-2xl">
                                Upload meeting recordings to automatically extract summaries, action items, and decisions.
                            </p>
                        </div>

                        {/* Tabs */}
                        <div className="flex flex-wrap gap-2 mb-6">
                            {[
                                { id: 'upload', label: 'Upload', shortLabel: 'Upload', icon: '📤' },
                                { id: 'list', label: 'All Meetings', shortLabel: 'List', icon: '📋' },
                                { id: 'summary', label: 'Summary', shortLabel: 'Summary', icon: '📊', disabled: !selectedMeetingId },
                                { id: 'actions', label: 'Action Items', shortLabel: 'Actions', icon: '✅', disabled: !selectedMeetingId },
                            ].map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => !tab.disabled && setActiveTab(tab.id as any)}
                                    disabled={tab.disabled}
                                    className={`
                                        flex-1 sm:flex-none px-4 sm:px-6 py-3 rounded-xl font-medium transition-all duration-200 text-xs sm:text-sm md:text-base
                                        ${activeTab === tab.id
                                            ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/30'
                                            : tab.disabled
                                                ? 'bg-slate-800/50 text-slate-500 cursor-not-allowed'
                                                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                                        }
                                    `}
                                >
                                    <span className="sm:inline hidden mr-2">{tab.icon}</span>
                                    <span className="sm:inline hidden">{tab.label}</span>
                                    <span className="sm:hidden">{tab.shortLabel}</span>
                                </button>
                            ))}
                        </div>

                        {/* Content */}
                        <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-4 sm:p-6 shadow-2xl">
                            {activeTab === 'upload' && (
                                <MeetingUpload
                                    onUploadComplete={(meetingId) => {
                                        setSelectedMeetingId(meetingId);
                                        setActiveTab('summary');
                                    }}
                                />
                            )}

                            {activeTab === 'list' && (
                                <MeetingList
                                    onSelectMeeting={(meetingId: string) => {
                                        setSelectedMeetingId(meetingId);
                                        setActiveTab('summary');
                                    }}
                                />
                            )}

                            {activeTab === 'summary' && selectedMeetingId && (
                                <MeetingSummary meetingId={selectedMeetingId} />
                            )}

                            {activeTab === 'actions' && selectedMeetingId && (
                                <ActionItemsView meetingId={selectedMeetingId} />
                            )}
                        </div>
                    </div>
                </div>
            </PMLoadingProvider>
        </QueryClientProvider>
    );
}

export default function MeetingPage() {
    return (
        <Suspense fallback={
            <div className="flex h-screen w-screen items-center justify-center bg-slate-900 text-white">
                Loading Meeting Notes...
            </div>
        }>
            <MeetingPageContent />
        </Suspense>
    );
}
