// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Card } from "~/components/ui/card";
import { useMyTasks } from "~/core/api/hooks/pm/use-tasks";
import { useMemo } from "react";

export function TeamAssignmentsView() {
  const { tasks, loading, error } = useMyTasks();

  // Group tasks by assignee
  const assignments = useMemo(() => {
    const byAssignee: Record<string, any[]> = {};
    const unassigned: any[] = [];

    tasks.forEach(task => {
      if (task.assigned_to) {
        const assignee = task.assigned_to;
        if (!byAssignee[assignee]) {
          byAssignee[assignee] = [];
        }
        // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
        byAssignee[assignee]!.push(task);
      } else {
        unassigned.push(task);
      }
    });

    return { byAssignee, unassigned };
  }, [tasks]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading assignments...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-red-500">Error loading assignments: {error.message}</div>
      </div>
    );
  }

  // Calculate totals for each assignee
  const assigneeTotals = Object.entries(assignments.byAssignee).map(([assigneeId, tasks]) => {
    const totalHours = tasks.reduce((sum, t) => sum + (t.estimated_hours || 0), 0);
    const completedCount = tasks.filter(t => 
      t.status && (t.status.toLowerCase().includes("done") || t.status.toLowerCase().includes("completed"))
    ).length;
    const highPriority = tasks.filter(t => t.priority === "high").reduce((sum, t) => sum + (t.estimated_hours || 0), 0);
    const mediumPriority = tasks.filter(t => t.priority === "medium").reduce((sum, t) => sum + (t.estimated_hours || 0), 0);
    const lowPriority = tasks.filter(t => !t.priority || t.priority === "low").reduce((sum, t) => sum + (t.estimated_hours || 0), 0);
    
    return {
      assigneeId,
      assigneeName: tasks[0].assigned_to || `User ${assigneeId}`,
      totalHours,
      tasks,
      tasksCount: tasks.length,
      completedCount,
      highPriority,
      mediumPriority,
      lowPriority,
    };
  });

  // Sort by total hours descending
  assigneeTotals.sort((a, b) => b.totalHours - a.totalHours);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Team Assignments</h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {Object.keys(assignments.byAssignee).length} team members
        </div>
      </div>

      {assigneeTotals.length === 0 && assignments.unassigned.length === 0 ? (
        <Card className="p-6">
          <div className="text-center text-gray-500 dark:text-gray-400 py-12">
            No tasks assigned
          </div>
        </Card>
      ) : (
        <>
          {/* Team Members */}
          <div className="space-y-4">
            {assigneeTotals.map((assignee) => (
              <Card key={assignee.assigneeId} className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="font-semibold text-gray-900 dark:text-white">
                    👤 {assignee.assigneeName}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Total: {assignee.totalHours.toFixed(1)}h
                  </div>
                </div>
                {(assignee.highPriority > 0 || assignee.mediumPriority > 0 || assignee.lowPriority > 0) && (
                  <div className="flex gap-2 mb-2">
                    {assignee.highPriority > 0 && (
                      <span className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded text-xs">
                        🔴 {assignee.highPriority.toFixed(1)}h
                      </span>
                    )}
                    {assignee.mediumPriority > 0 && (
                      <span className="px-2 py-1 bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 rounded text-xs">
                        🟡 {assignee.mediumPriority.toFixed(1)}h
                      </span>
                    )}
                    {assignee.lowPriority > 0 && (
                      <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs">
                        🔵 {assignee.lowPriority.toFixed(1)}h
                      </span>
                    )}
                  </div>
                )}
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Tasks: {assignee.tasksCount} | Completed: {assignee.completedCount}
                </div>
              </Card>
            ))}
          </div>

          {/* Unassigned Tasks */}
          {assignments.unassigned.length > 0 && (
            <Card className="p-4">
              <div className="font-semibold text-gray-900 dark:text-white mb-3">
                ⚠️ Unassigned Tasks ({assignments.unassigned.length})
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Total: {assignments.unassigned.reduce((sum, t) => sum + (t.estimated_hours || 0), 0).toFixed(1)}h
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

