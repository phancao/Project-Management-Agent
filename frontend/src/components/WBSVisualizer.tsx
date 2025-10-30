"use client";

import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Circle, Clock, TrendingUp, FileText } from 'lucide-react';

interface WBSTask {
  title: string;
  description?: string;
  level: number;
  estimated_hours?: number;
  priority: string;
  parent_id?: string;
}

interface WBSStructure {
  phases: Array<{
    title: string;
    level: number;
    estimated_hours: number;
    priority: string;
    deliverables?: Array<{
      title: string;
      level: number;
      estimated_hours: number;
      priority: string;
      tasks?: WBSTask[];
    }>;
  }>;
}

interface WBSVisualizerProps {
  wbsData?: {
    project_name: string;
    wbs_structure: WBSStructure;
    levels: number;
    total_tasks: number;
    use_research?: boolean;
  };
  onClose?: () => void;
}

export function WBSVisualizer({ wbsData, onClose }: WBSVisualizerProps) {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [selectedTask, setSelectedTask] = useState<WBSTask | null>(null);

  if (!wbsData) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h2 className="text-2xl font-bold mb-4">Work Breakdown Structure</h2>
        <p className="text-gray-600">No WBS data available. Create a WBS for your project first.</p>
      </div>
    );
  }

  const toggleExpand = (itemId: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(itemId)) {
      newExpanded.delete(itemId);
    } else {
      newExpanded.add(itemId);
    }
    setExpandedItems(newExpanded);
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800 border-red-300';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'low': return 'bg-green-100 text-green-800 border-green-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getLevelIndent = (level: number) => {
    return level * 24; // 24px per level
  };

  const calculateTotalHours = (phases: any[]): number => {
    return phases.reduce((total, phase) => {
      const phaseHours = phase.estimated_hours || 0;
      const deliverablesHours = phase.deliverables?.reduce((sum: number, d: any) => {
        const dHours = d.estimated_hours || 0;
        const tasksHours = d.tasks?.reduce((taskSum: number, t: any) => 
          taskSum + (t.estimated_hours || 0), 0) || 0;
        return sum + dHours + tasksHours;
      }, 0) || 0;
      return total + phaseHours + deliverablesHours;
    }, 0);
  };

  const renderTask = (task: WBSTask, phaseIndex: number, delivIndex?: number) => {
    const taskId = `phase-${phaseIndex}-deliv-${delivIndex || 'none'}-task-${task.title}`;
    const indent = getLevelIndent(task.level);
    
    return (
      <div
        key={taskId}
        className="flex items-start space-x-2 py-2 hover:bg-gray-50 transition-colors cursor-pointer rounded px-2"
        style={{ paddingLeft: `${indent + 8}px` }}
        onClick={() => setSelectedTask(task)}
      >
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <Circle className="w-3 h-3 flex-shrink-0" />
            <span className="text-sm font-medium text-gray-900">{task.title}</span>
            {task.estimated_hours && (
              <span className="text-xs text-gray-500 flex items-center">
                <Clock className="w-3 h-3 mr-1" />
                {task.estimated_hours}h
              </span>
            )}
            <span className={`text-xs px-2 py-0.5 rounded-full border ${getPriorityColor(task.priority)}`}>
              {task.priority}
            </span>
          </div>
          {task.description && (
            <p className="text-xs text-gray-600 mt-1 ml-5">{task.description}</p>
          )}
        </div>
      </div>
    );
  };

  const renderDeliverable = (deliverable: any, phaseIndex: number, delivIndex: number) => {
    const delivId = `phase-${phaseIndex}-deliv-${delivIndex}`;
    const isExpanded = expandedItems.has(delivId);
    const indent = getLevelIndent(deliverable.level);

    return (
      <div key={delivId} className="border-l-2 border-blue-200">
        <div
          className="flex items-center py-3 px-2 hover:bg-blue-50 transition-colors cursor-pointer rounded"
          style={{ paddingLeft: `${indent + 8}px` }}
          onClick={() => toggleExpand(delivId)}
        >
          {deliverable.tasks && deliverable.tasks.length > 0 && (
            <button className="mr-2">
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-500" />
              )}
            </button>
          )}
          <FileText className="w-4 h-4 text-blue-600 mr-2" />
          <span className="font-semibold text-gray-900">{deliverable.title}</span>
          {deliverable.estimated_hours && (
            <span className="text-xs text-gray-500 ml-auto flex items-center">
              <Clock className="w-3 h-3 mr-1" />
              {deliverable.estimated_hours}h
            </span>
          )}
          <span className={`text-xs px-2 py-0.5 rounded-full border ml-2 ${getPriorityColor(deliverable.priority)}`}>
            {deliverable.priority}
          </span>
        </div>
        
        {isExpanded && deliverable.tasks && deliverable.tasks.length > 0 && (
          <div className="ml-6">
            {deliverable.tasks.map((task: WBSTask, taskIndex: number) => 
              renderTask(task, phaseIndex, delivIndex)
            )}
          </div>
        )}
      </div>
    );
  };

  const renderPhase = (phase: any, phaseIndex: number) => {
    const phaseId = `phase-${phaseIndex}`;
    const isExpanded = expandedItems.has(phaseId);
    const hasDeliverables = phase.deliverables && phase.deliverables.length > 0;
    const indent = getLevelIndent(phase.level);

    return (
      <div key={phaseId} className="border-l-4 border-blue-500 mb-4 bg-white shadow-sm rounded-lg overflow-hidden">
        <div
          className="flex items-center py-4 px-4 bg-gradient-to-r from-blue-50 to-white hover:from-blue-100 transition-colors cursor-pointer"
          onClick={() => hasDeliverables && toggleExpand(phaseId)}
        >
          {hasDeliverables && (
            <button className="mr-3">
              {isExpanded ? (
                <ChevronDown className="w-5 h-5 text-blue-600" />
              ) : (
                <ChevronRight className="w-5 h-5 text-blue-600" />
              )}
            </button>
          )}
          <Circle className="w-5 h-5 text-blue-600 mr-2" fill="currentColor" />
          <div className="flex-1">
            <h3 className="text-lg font-bold text-gray-900">{phase.title}</h3>
            <div className="flex items-center space-x-3 mt-1">
              {phase.estimated_hours && (
                <span className="text-sm text-gray-600 flex items-center">
                  <Clock className="w-4 h-4 mr-1" />
                  {phase.estimated_hours} hours
                </span>
              )}
              <span className={`text-xs px-2 py-1 rounded-full border ${getPriorityColor(phase.priority)}`}>
                {phase.priority.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
        
        {isExpanded && hasDeliverables && (
          <div className="p-4 bg-gray-50">
            {phase.deliverables.map((deliverable: any, delivIndex: number) => 
              renderDeliverable(deliverable, phaseIndex, delivIndex)
            )}
          </div>
        )}
      </div>
    );
  };

  const totalHours = calculateTotalHours(wbsData.wbs_structure.phases);

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4 bg-gradient-to-r from-blue-50 to-white">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Work Breakdown Structure</h2>
            <p className="text-sm text-gray-600 mt-1">{wbsData.project_name}</p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-white rounded-lg transition-colors"
            >
              Close
            </button>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mt-4">
          <div className="bg-white rounded-lg p-3 border border-gray-200">
            <div className="text-xs text-gray-600 mb-1">Levels</div>
            <div className="text-2xl font-bold text-blue-600">{wbsData.levels}</div>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-200">
            <div className="text-xs text-gray-600 mb-1">Total Tasks</div>
            <div className="text-2xl font-bold text-green-600">{wbsData.total_tasks}</div>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-200">
            <div className="text-xs text-gray-600 mb-1">Total Hours</div>
            <div className="text-2xl font-bold text-purple-600">{totalHours}</div>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-200">
            <div className="text-xs text-gray-600 mb-1">Estimated Weeks</div>
            <div className="text-2xl font-bold text-orange-600">{Math.ceil(totalHours / 40)}</div>
          </div>
        </div>
      </div>

      {/* WBS Tree */}
      <div className="p-6 max-h-[600px] overflow-y-auto">
        {wbsData.wbs_structure.phases.map((phase, index) => renderPhase(phase, index))}
      </div>

      {/* Task Details Panel */}
      {selectedTask && (
        <div className="border-t border-gray-200 p-6 bg-gray-50">
          <h3 className="text-lg font-semibold mb-3">Task Details</h3>
          <div className="space-y-2">
            <div>
              <span className="text-sm font-medium text-gray-700">Title:</span>
              <p className="text-gray-900">{selectedTask.title}</p>
            </div>
            {selectedTask.description && (
              <div>
                <span className="text-sm font-medium text-gray-700">Description:</span>
                <p className="text-gray-900">{selectedTask.description}</p>
              </div>
            )}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <span className="text-sm font-medium text-gray-700">Level:</span>
                <p className="text-gray-900">Level {selectedTask.level}</p>
              </div>
              {selectedTask.estimated_hours && (
                <div>
                  <span className="text-sm font-medium text-gray-700">Estimated Hours:</span>
                  <p className="text-gray-900">{selectedTask.estimated_hours}h</p>
                </div>
              )}
              <div>
                <span className="text-sm font-medium text-gray-700">Priority:</span>
                <p className="text-gray-900 capitalize">{selectedTask.priority}</p>
              </div>
            </div>
          </div>
          <button
            onClick={() => setSelectedTask(null)}
            className="mt-4 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
          >
            Close Details
          </button>
        </div>
      )}
    </div>
  );
}
