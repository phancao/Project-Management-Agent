"use client";

import React, { useState, useEffect } from 'react';
import { FileText, Download, Calendar, TrendingUp, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { projectAPI, Project } from '@/services/api';

interface ReportData {
  project_id: string;
  project_name: string;
  report_type: string;
  format: string;
  generated_at: string;
  content: string;
  sections: number;
  include_research: boolean;
}

interface ReportsDashboardProps {
  onClose?: () => void;
}

export function ReportsDashboard({ onClose }: ReportsDashboardProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [reportType, setReportType] = useState<string>('status');
  const [isGenerating, setIsGenerating] = useState(false);
  const [report, setReport] = useState<ReportData | null>(null);
  const [recentReports, setRecentReports] = useState<ReportData[]>([]);

  useEffect(() => {
    async function fetchProjects() {
      try {
        const data = await projectAPI.list();
        setProjects(data);
        if (data.length > 0) {
          setSelectedProject(data[0].id);
        }
      } catch (err) {
        console.error('Error fetching projects:', err);
      }
    }
    fetchProjects();
  }, []);

  const handleGenerateReport = async () => {
    if (!selectedProject) {
      alert('Please select a project');
      return;
    }

    setIsGenerating(true);
    try {
      // For now, we'll simulate report generation
      // In production, this would call the backend API
      
      const project = projects.find(p => p.id === selectedProject);
      if (!project) return;

      // Create mock report content
      const mockContent = generateMockReport(project, reportType);

      const newReport: ReportData = {
        project_id: selectedProject,
        project_name: project.name,
        report_type: reportType,
        format: 'markdown',
        generated_at: new Date().toISOString(),
        content: mockContent,
        sections: 4,
        include_research: true,
      };

      setReport(newReport);
      setRecentReports(prev => [newReport, ...prev].slice(0, 5));
    } catch (err) {
      console.error('Error generating report:', err);
      alert('Failed to generate report');
    } finally {
      setIsGenerating(false);
    }
  };

  const generateMockReport = (project: Project, type: string): string => {
    if (type === 'status') {
      return `# ${project.name} - Status Report

## Executive Summary
**Project:** ${project.name}
**Status:** ${project.status || 'In Progress'}
**Priority:** ${project.priority || 'Medium'}

## Current Status
- Total Tasks: 12
- Completed: 8 (67%)
- In Progress: 3
- To Do: 1

## Progress
Project is 67% complete based on estimated hours.

**Completed Hours:** 320h / 480h

## Team
- Developer 1
- Developer 2
- Designer 1

*Report generated on ${new Date().toLocaleString()}*
`;
    }

    return `# ${project.name} Report\n\nReport content for ${type}...`;
  };

  const handleDownloadReport = () => {
    if (!report) return;

    const blob = new Blob([report.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.project_name}_${report.report_type}_${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getReportTypeIcon = (type: string) => {
    switch (type) {
      case 'status': return <TrendingUp className="w-4 h-4" />;
      case 'progress': return <Clock className="w-4 h-4" />;
      case 'summary': return <FileText className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Project Reports</h2>
            <p className="text-sm text-gray-600 mt-1">Generate and view project reports</p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>

      <div className="p-6">
        {!report ? (
          <>
            {/* Report Generator */}
            <div className="space-y-6 mb-8">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Project
                </label>
                <select
                  value={selectedProject}
                  onChange={(e) => setSelectedProject(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isGenerating}
                >
                  <option value="">Select a project...</option>
                  {projects.map(project => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Report Type
                </label>
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isGenerating}
                >
                  <option value="status">Status Report</option>
                  <option value="progress">Progress Report</option>
                  <option value="summary">Summary Report</option>
                  <option value="detailed">Detailed Report</option>
                </select>
              </div>

              <button
                onClick={handleGenerateReport}
                disabled={!selectedProject || isGenerating}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                {isGenerating ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4" />
                    <span>Generate Report</span>
                  </>
                )}
              </button>
            </div>

            {/* Recent Reports */}
            {recentReports.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Recent Reports</h3>
                <div className="space-y-2">
                  {recentReports.map((recentReport, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors cursor-pointer"
                      onClick={() => setReport(recentReport)}
                    >
                      <div className="flex items-center space-x-3">
                        {getReportTypeIcon(recentReport.report_type)}
                        <div>
                          <div className="font-medium text-gray-900">{recentReport.project_name}</div>
                          <div className="text-sm text-gray-600 capitalize">{recentReport.report_type} Report</div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500">
                        {new Date(recentReport.generated_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            {/* Report Viewer */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getReportTypeIcon(report.report_type)}
                  <h3 className="text-lg font-semibold text-gray-900">
                    {report.project_name} - {report.report_type.charAt(0).toUpperCase() + report.report_type.slice(1)} Report
                  </h3>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={handleDownloadReport}
                    className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-sm flex items-center space-x-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download</span>
                  </button>
                  <button
                    onClick={() => setReport(null)}
                    className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
                  >
                    Back
                  </button>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans">
                    {report.content}
                  </pre>
                </div>
              </div>

              <div className="text-xs text-gray-500 text-center">
                Generated on {new Date(report.generated_at).toLocaleString()}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
