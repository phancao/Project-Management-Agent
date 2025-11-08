// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Card } from "~/components/ui/card";
import { useSprintReport } from "~/core/api/hooks/pm/use-analytics";
import { useActiveProject } from "~/core/api/hooks/pm/use-projects";
import { useSprints } from "~/core/api/hooks/pm/use-sprints";

export function SprintReportView() {
  const { activeProject } = useActiveProject();
  const { sprints } = useSprints(activeProject?.id || null);
  
  // Get the most recent active or completed sprint
  const currentSprint = sprints?.find(s => s.status === "active") || sprints?.[0];
  
  const { data: report, isLoading: loading, error } = useSprintReport(
    currentSprint?.id || null,
    activeProject?.id || null
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading sprint report...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-red-500">Error loading data: {error.message}</div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">No sprint data available</div>
      </div>
    );
  }

  const completionRate = report.commitment.completion_rate * 100;
  const capacityUtilized = report.team_performance.capacity_utilized * 100;
  const scopeStability = report.scope_changes.scope_stability * 100;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{report.sprint_name} Report</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {new Date(report.duration.start).toLocaleDateString()} - {new Date(report.duration.end).toLocaleDateString()} ({report.duration.days} days)
          </p>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${completionRate >= 90 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : completionRate >= 70 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}`}>
          {completionRate.toFixed(0)}% Complete
        </div>
      </div>

      {/* Commitment Metrics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Sprint Commitment</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Planned Points</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{report.commitment.planned_points.toFixed(1)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Completed Points</div>
            <div className="text-2xl font-bold text-green-600">{report.commitment.completed_points.toFixed(1)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Planned Items</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{report.commitment.planned_items}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Completed Items</div>
            <div className="text-2xl font-bold text-green-600">{report.commitment.completed_items}</div>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
            <span>Completion Rate</span>
            <span className="font-semibold">{completionRate.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
            <div 
              className={`h-3 rounded-full transition-all ${completionRate >= 90 ? 'bg-green-500' : completionRate >= 70 ? 'bg-yellow-500' : 'bg-red-500'}`}
              style={{ width: `${Math.min(completionRate, 100)}%` }}
            ></div>
          </div>
        </div>
      </Card>

      {/* Scope Changes */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Scope Changes</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Items Added</div>
            <div className="text-2xl font-bold text-blue-600">+{report.scope_changes.added}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Items Removed</div>
            <div className="text-2xl font-bold text-red-600">-{report.scope_changes.removed}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Net Change</div>
            <div className={`text-2xl font-bold ${report.scope_changes.net_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {report.scope_changes.net_change >= 0 ? '+' : ''}{report.scope_changes.net_change}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Stability Score</div>
            <div className="text-2xl font-bold text-purple-600">{scopeStability.toFixed(0)}%</div>
          </div>
        </div>
      </Card>

      {/* Work Breakdown & Team Performance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Work Breakdown */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Work Breakdown</h3>
          <div className="space-y-3">
            {Object.entries(report.work_breakdown).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${type === 'story' ? 'bg-blue-500' : type === 'bug' ? 'bg-red-500' : 'bg-gray-500'}`}></div>
                  <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">{type}s</span>
                </div>
                <span className="text-lg font-bold text-gray-900 dark:text-white">{count}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Team Performance */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Team Performance</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
                <span>Velocity</span>
                <span className="font-semibold">{report.team_performance.velocity.toFixed(1)} pts</span>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
                <span>Team Size</span>
                <span className="font-semibold">{report.team_performance.team_size} members</span>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                <span>Capacity Utilized</span>
                <span className="font-semibold">{capacityUtilized.toFixed(0)}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${capacityUtilized >= 80 && capacityUtilized <= 95 ? 'bg-green-500' : capacityUtilized > 95 ? 'bg-red-500' : 'bg-yellow-500'}`}
                  style={{ width: `${Math.min(capacityUtilized, 100)}%` }}
                ></div>
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                <span className="font-semibold">{report.team_performance.capacity_used.toFixed(0)}h</span> / {report.team_performance.capacity_hours.toFixed(0)}h
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Highlights & Concerns */}
      {(report.highlights.length > 0 || report.concerns.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Highlights */}
          {report.highlights.length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-green-600 dark:text-green-400 mb-4">✨ Highlights</h3>
              <ul className="space-y-2">
                {report.highlights.map((highlight, index) => (
                  <li key={index} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                    <span className="text-green-500 mt-0.5">✓</span>
                    <span>{highlight}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Concerns */}
          {report.concerns.length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-yellow-600 dark:text-yellow-400 mb-4">⚠️ Concerns</h3>
              <ul className="space-y-2">
                {report.concerns.map((concern, index) => (
                  <li key={index} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                    <span className="text-yellow-500 mt-0.5">!</span>
                    <span>{concern}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

