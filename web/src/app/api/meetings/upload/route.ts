import { NextRequest, NextResponse } from 'next/server';
import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { v4 as uuid } from 'uuid';

const UPLOAD_DIR = process.env.MEETING_UPLOAD_DIR || './uploads/meetings';

/**
 * POST /api/meetings/upload
 * Upload a meeting recording
 */
export async function POST(request: NextRequest) {
    try {
        const formData = await request.formData();
        const file = formData.get('file') as File;
        const title = formData.get('title') as string || 'Untitled Meeting';
        const participants = formData.get('participants') as string || '';

        if (!file) {
            return NextResponse.json(
                { error: 'No file provided' },
                { status: 400 }
            );
        }

        // Generate meeting ID
        const meetingId = `mtg_${uuid().replace(/-/g, '').slice(0, 12)}`;

        // Ensure upload directory exists
        await mkdir(UPLOAD_DIR, { recursive: true });

        // Save file
        const ext = file.name.split('.').pop() || 'mp3';
        const filePath = join(UPLOAD_DIR, `${meetingId}.${ext}`);
        const bytes = await file.arrayBuffer();
        await writeFile(filePath, Buffer.from(bytes));

        // Store meeting metadata (in production, save to database)
        const meeting = {
            id: meetingId,
            title,
            participants: participants.split(',').map(p => p.trim()).filter(Boolean),
            filePath,
            status: 'pending',
            createdAt: new Date().toISOString(),
        };

        // In production, would call MCP meeting server to register the meeting

        return NextResponse.json({
            meetingId: meeting.id,
            title: meeting.title,
            message: 'File uploaded successfully',
        });
    } catch (error) {
        console.error('Upload failed:', error);
        return NextResponse.json(
            { error: 'Upload failed' },
            { status: 500 }
        );
    }
}

export const config = {
    api: {
        bodyParser: false,
    },
};
