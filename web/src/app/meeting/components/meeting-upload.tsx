'use client';

import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';

interface MeetingUploadProps {
    onUploadComplete: (meetingId: string) => void;
    projectId?: string | null;
}

export default function MeetingUpload({ onUploadComplete, projectId }: MeetingUploadProps) {
    const [uploading, setUploading] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [title, setTitle] = useState('');
    const [participants, setParticipants] = useState('');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [progress, setProgress] = useState<string>('');

    const onDrop = useCallback((acceptedFiles: File[]) => {
        const file = acceptedFiles[0];
        if (file) {
            setSelectedFile(file);
            // Auto-set title from filename
            const filename = file.name.replace(/\.[^/.]+$/, '');
            if (!title) {
                setTitle(filename);
            }
        }
    }, [title]);

    // Fetch participants when project changes
    useEffect(() => {
        if (projectId) {
            fetch(`/api/users?projectId=${projectId}`)
                .then(res => res.json())
                .then(data => {
                    if (data.users && Array.isArray(data.users)) {
                        const names = data.users.map((u: any) => u.name).join(', ');
                        setParticipants(names);
                    }
                })
                .catch(err => console.error('Failed to fetch users:', err));
        }
    }, [projectId]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'audio/*': ['.mp3', '.wav', '.m4a', '.ogg', '.flac'],
            'video/*': ['.mp4', '.webm', '.mov'],
        },
        maxSize: 500 * 1024 * 1024, // 500MB
        multiple: false,
    });

    const handleUpload = async () => {
        if (!selectedFile) {
            setError('Please select a file');
            return;
        }

        try {
            setUploading(true);
            setError(null);
            setProgress('Uploading file...');

            // Create form data
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('title', title || 'Untitled Meeting');
            formData.append('participants', participants);

            if (projectId) {
                formData.append('projectId', projectId);
            }

            // Upload to backend
            const uploadRes = await fetch('/api/meetings/upload', {
                method: 'POST',
                body: formData,
            });

            if (!uploadRes.ok) {
                throw new Error('Upload failed');
            }

            const { meetingId } = await uploadRes.json();

            setUploading(false);
            setProcessing(true);
            setProgress('Transcribing audio...');

            // Process the meeting
            const processRes = await fetch('/api/meetings/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ meetingId }),
            });

            if (!processRes.ok) {
                throw new Error('Processing failed');
            }

            setProgress('Analyzing content...');

            // Poll for completion or use SSE
            const result = await processRes.json();

            setProcessing(false);
            setProgress('');
            onUploadComplete(result.meetingId);

        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
            setUploading(false);
            setProcessing(false);
            setProgress('');
        }
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024 * 1024) {
            return `${(bytes / 1024).toFixed(1)} KB`;
        }
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return (
        <div className="max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-6">Upload Meeting Recording</h2>

            {!projectId && (
                <div className="mb-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-200 text-sm flex items-start gap-3">
                    <span className="text-xl">⚠️</span>
                    <div>
                        <p className="font-medium">No Project Selected</p>
                        <p className="mt-1 opacity-80">
                            Please select a project from the top header to associate this meeting with project data.
                            Uploading without a project will create an orphaned meeting.
                        </p>
                    </div>
                </div>
            )}

            {/* Dropzone */}
            <div
                {...getRootProps()}
                className={`
          border-2 border-dashed rounded-xl p-4 sm:p-8 text-center cursor-pointer
          transition-all duration-200
          ${isDragActive
                        ? 'border-purple-500 bg-purple-500/10'
                        : selectedFile
                            ? 'border-green-500 bg-green-500/10'
                            : 'border-slate-600 hover:border-purple-400 hover:bg-slate-700/30'
                    }
        `}
            >
                <input {...getInputProps()} />

                {selectedFile ? (
                    <div>
                        <div className="text-3xl sm:text-4xl mb-4">✅</div>
                        <p className="text-white font-medium text-sm sm:text-base truncate px-4">{selectedFile.name}</p>
                        <p className="text-slate-400 text-xs sm:text-sm">{formatFileSize(selectedFile.size)}</p>
                        <p className="text-purple-400 text-xs mt-2">Click or drop to replace</p>
                    </div>
                ) : isDragActive ? (
                    <div>
                        <div className="text-3xl sm:text-4xl mb-4">📥</div>
                        <p className="text-purple-400 font-medium">Drop the file here</p>
                    </div>
                ) : (
                    <div>
                        <div className="text-3xl sm:text-4xl mb-4">🎙️</div>
                        <p className="text-white font-medium mb-2 text-sm sm:text-base">
                            Drag & drop a meeting recording here
                        </p>
                        <p className="text-slate-400 text-xs sm:text-sm px-4">
                            Supports MP3, WAV, M4A, OGG, MP4, WebM (max 500MB)
                        </p>
                    </div>
                )}
            </div>

            {/* Meeting Details */}
            <div className="mt-6 space-y-4">
                <div>
                    <label className="block text-slate-300 mb-2">Meeting Title</label>
                    <input
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        placeholder="Weekly Standup"
                        className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg
                       text-white placeholder-slate-400 focus:outline-none focus:border-purple-500"
                    />
                </div>

                <div>
                    <label className="block text-slate-300 mb-2">
                        Participants (comma-separated)
                    </label>
                    <input
                        type="text"
                        value={participants}
                        onChange={(e) => setParticipants(e.target.value)}
                        placeholder="Alice, Bob, Charlie"
                        className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg
                       text-white placeholder-slate-400 focus:outline-none focus:border-purple-500"
                    />
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
                    {error}
                </div>
            )}

            {/* Progress */}
            {progress && (
                <div className="mt-4 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                    <div className="flex items-center">
                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-purple-500 border-t-transparent mr-3" />
                        <span className="text-purple-400">{progress}</span>
                    </div>
                </div>
            )}

            {/* Upload Button */}
            <button
                onClick={handleUpload}
                disabled={!selectedFile || uploading || processing}
                className={`
          w-full mt-6 py-4 rounded-xl font-medium text-lg transition-all duration-200
          ${!selectedFile || uploading || processing
                        ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                        : 'bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-500 hover:to-pink-500 shadow-lg shadow-purple-500/30'
                    }
        `}
            >
                {uploading ? 'Uploading...' : processing ? 'Processing...' : 'Upload & Analyze'}
            </button>

            {/* Features */}
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
                {[
                    { icon: '🎯', title: 'Auto Transcribe', desc: 'Speech to text' },
                    { icon: '📝', title: 'Smart Summary', desc: 'Key points extracted' },
                    { icon: '✅', title: 'Action Items', desc: 'Tasks auto-created' },
                ].map((feature) => (
                    <div key={feature.title} className="p-4 bg-slate-700/30 rounded-lg">
                        <div className="text-2xl mb-2">{feature.icon}</div>
                        <div className="text-white font-medium">{feature.title}</div>
                        <div className="text-slate-400 text-sm">{feature.desc}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
