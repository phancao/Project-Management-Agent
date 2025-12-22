'use client';

import { useState, useEffect } from 'react';

interface ActionItem {
    id: string;
    description: string;
    assigneeName: string | null;
    dueDate: string | null;
    dueDateText: string | null;
    priority: 'critical' | 'high' | 'medium' | 'low';
    status: 'pending' | 'in_progress' | 'completed';
    sourceQuote: string | null;
    pmTaskId: string | null;
}

interface ActionItemsViewProps {
    meetingId: string;
}

export default function ActionItemsView({ meetingId }: ActionItemsViewProps) {
    const [actionItems, setActionItems] = useState<ActionItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState<Set<string>>(new Set());

    useEffect(() => {
        fetchActionItems();
    }, [meetingId]);

    const fetchActionItems = async () => {
        try {
            setLoading(true);
            const res = await fetch(`/api/meetings/${meetingId}/action-items`);
            if (res.ok) {
                const data = await res.json();
                setActionItems(data.actionItems || []);
            }
        } catch (err) {
            console.error('Failed to fetch action items:', err);
        } finally {
            setLoading(false);
        }
    };

    const createPMTask = async (actionItem: ActionItem) => {
        try {
            setCreating((prev) => new Set(prev).add(actionItem.id));

            const res = await fetch(`/api/meetings/${meetingId}/create-task`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ actionItemId: actionItem.id }),
            });

            if (res.ok) {
                const data = await res.json();
                setActionItems((prev) =>
                    prev.map((item) =>
                        item.id === actionItem.id
                            ? { ...item, pmTaskId: data.taskId }
                            : item
                    )
                );
            }
        } catch (err) {
            console.error('Failed to create task:', err);
        } finally {
            setCreating((prev) => {
                const next = new Set(prev);
                next.delete(actionItem.id);
                return next;
            });
        }
    };

    const createAllTasks = async () => {
        const pendingItems = actionItems.filter((item) => !item.pmTaskId);
        for (const item of pendingItems) {
            await createPMTask(item);
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'critical': return 'bg-red-500/20 text-red-400 border-red-500/30';
            case 'high': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
            case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
            case 'low': return 'bg-green-500/20 text-green-400 border-green-500/30';
            default: return 'bg-slate-500/20 text-slate-400';
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-purple-500 border-t-transparent" />
            </div>
        );
    }

    const pendingCount = actionItems.filter((item) => !item.pmTaskId).length;

    return (
        <div>
            {/* Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-white">Action Items</h2>
                    <p className="text-slate-400">
                        {actionItems.length} items extracted • {pendingCount} pending task creation
                    </p>
                </div>

                {pendingCount > 0 && (
                    <button
                        onClick={createAllTasks}
                        className="w-full sm:w-auto px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl
                       font-medium hover:from-purple-500 hover:to-pink-500 transition-all
                       shadow-lg shadow-purple-500/30 text-sm"
                    >
                        Create All Tasks ({pendingCount})
                    </button>
                )}
            </div>

            {/* Action Items List */}
            {actionItems.length === 0 ? (
                <div className="text-center py-12">
                    <div className="text-4xl mb-4">📋</div>
                    <p className="text-slate-400">No action items found in this meeting</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {actionItems.map((item) => (
                        <div
                            key={item.id}
                            className={`
                p-4 rounded-xl border transition-all
                ${item.pmTaskId
                                    ? 'bg-green-500/5 border-green-500/30'
                                    : 'bg-slate-700/30 border-slate-600/50'
                                }
              `}
                        >
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                    {/* Priority Badge */}
                                    <div className="flex items-center gap-2 mb-2">
                                        <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getPriorityColor(item.priority)}`}>
                                            {item.priority.toUpperCase()}
                                        </span>
                                        {item.pmTaskId && (
                                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-500/20 text-green-400">
                                                ✓ Task Created
                                            </span>
                                        )}
                                    </div>

                                    {/* Description */}
                                    <p className="text-white font-medium">{item.description}</p>

                                    {/* Metadata */}
                                    <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
                                        {item.assigneeName && (
                                            <span>👤 {item.assigneeName}</span>
                                        )}
                                        {item.dueDate && (
                                            <span>📅 {new Date(item.dueDate).toLocaleDateString()}</span>
                                        )}
                                        {item.dueDateText && !item.dueDate && (
                                            <span>📅 {item.dueDateText}</span>
                                        )}
                                    </div>

                                    {/* Source Quote */}
                                    {item.sourceQuote && (
                                        <div className="mt-3 p-3 bg-slate-800/50 rounded-lg text-sm text-slate-400 italic">
                                            "{item.sourceQuote}"
                                        </div>
                                    )}
                                </div>

                                {/* Actions */}
                                <div className="flex-shrink-0">
                                    {item.pmTaskId ? (
                                        <a
                                            href={`/pm/tasks/${item.pmTaskId}`}
                                            className="px-4 py-2 bg-green-600/20 text-green-400 rounded-lg text-sm
                                 hover:bg-green-600/30 transition-colors"
                                        >
                                            View Task →
                                        </a>
                                    ) : (
                                        <button
                                            onClick={() => createPMTask(item)}
                                            disabled={creating.has(item.id)}
                                            className={`
                        px-4 py-2 rounded-lg text-sm font-medium transition-all
                        ${creating.has(item.id)
                                                    ? 'bg-slate-600 text-slate-400 cursor-wait'
                                                    : 'bg-purple-600/20 text-purple-400 hover:bg-purple-600/30'
                                                }
                      `}
                                        >
                                            {creating.has(item.id) ? (
                                                <span className="flex items-center">
                                                    <span className="animate-spin mr-2">⏳</span>
                                                    Creating...
                                                </span>
                                            ) : (
                                                'Create Task'
                                            )}
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
