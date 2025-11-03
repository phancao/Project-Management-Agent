// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { DndContext, DragEndEvent, DragOverlay, DragStartEvent, PointerSensor, useSensor, useSensors, closestCenter, useDroppable } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useState } from "react";
import { useMyTasks } from "~/core/api/hooks/pm/use-tasks";

function TaskCard({ task }: { task: any }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow cursor-move"
    >
      <div className="font-medium text-sm text-gray-900 dark:text-white mb-2">
        {task.title}
      </div>
      <div className="flex items-center gap-2 text-xs">
        {task.priority && (
          <span className={`px-2 py-0.5 rounded ${
            task.priority === "high" ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" :
            task.priority === "medium" ? "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200" :
            "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
          }`}>
            {task.priority}
          </span>
        )}
        {task.estimated_hours && (
          <span className="text-gray-500 dark:text-gray-400">
            ⏱️ {task.estimated_hours}h
          </span>
        )}
      </div>
    </div>
  );
}

function Column({ column, tasks }: { column: { id: string; title: string }; tasks: any[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  
  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between p-3 bg-gray-100 dark:bg-gray-800 rounded-t-lg">
        <h3 className="font-semibold text-gray-900 dark:text-white">{column.title}</h3>
        <span className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-sm font-medium text-gray-700 dark:text-gray-300">
          {tasks.length}
        </span>
      </div>
      <div 
        ref={setNodeRef}
        className={`flex-1 bg-gray-50 dark:bg-gray-900 rounded-b-lg p-3 min-h-[400px] border border-gray-200 dark:border-gray-700 overflow-y-auto ${isOver ? 'bg-blue-50 dark:bg-blue-950' : ''}`}
      >
        {tasks.length === 0 ? (
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
            No tasks
          </div>
        ) : (
          <div className="space-y-2">
            {tasks.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function SprintBoardView() {
  const { tasks, loading, error } = useMyTasks();
  const [activeId, setActiveId] = useState<string | null>(null);
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    // Find the task
    const task = tasks.find(t => t.id === activeId);
    if (!task) return;

    // Map column IDs to status
    const statusMap: Record<string, string> = {
      'todo': 'todo',
      'in-progress': 'in_progress',
      'review': 'review',
      'done': 'completed',
    };

    const newStatus = statusMap[overId];
    if (!newStatus || newStatus === task.status) return;

    // Update task status via API
    fetch(`http://localhost:8000/api/pm/tasks/${task.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    }).catch(err => console.error('Failed to update task:', err));
  };

  // Group tasks by status
  const todoTasks = tasks.filter(t => 
    !t.status || t.status === "None" || t.status.toLowerCase().includes("todo") || t.status.toLowerCase().includes("new")
  );
  const inProgressTasks = tasks.filter(t => 
    t.status && (t.status.toLowerCase().includes("progress") || t.status.toLowerCase().includes("in_progress"))
  );
  const reviewTasks = tasks.filter(t => 
    t.status && (t.status.toLowerCase().includes("review") || t.status.toLowerCase().includes("pending"))
  );
  const doneTasks = tasks.filter(t => 
    t.status && (t.status.toLowerCase().includes("done") || t.status.toLowerCase().includes("completed") || t.status.toLowerCase().includes("closed"))
  );

  const columns = [
    { id: "todo", title: "To Do", tasks: todoTasks },
    { id: "in-progress", title: "In Progress", tasks: inProgressTasks },
    { id: "review", title: "Review", tasks: reviewTasks },
    { id: "done", title: "Done", tasks: doneTasks },
  ];

  const activeTask = activeId ? tasks.find(t => t.id === activeId) : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading board...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-red-500">Error loading tasks: {error.message}</div>
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Sprint Board</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              My Tasks - {tasks.length} total
            </p>
          </div>
        </div>

        {/* Kanban Board */}
        <div className="grid grid-cols-4 gap-4">
          {columns.map((column) => (
            <Column key={column.id} column={{ id: column.id, title: column.title }} tasks={column.tasks} />
          ))}
        </div>
      </div>

      <DragOverlay>
        {activeTask ? <TaskCard task={activeTask} /> : null}
      </DragOverlay>
    </DndContext>
  );
}
