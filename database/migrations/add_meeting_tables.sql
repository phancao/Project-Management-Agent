-- Migration: Add Meeting Tables
-- Description: Adds tables for storing meeting data, transcripts, and action items.

-- Meetings table
CREATE TABLE IF NOT EXISTS meetings (
    id VARCHAR(50) PRIMARY KEY, -- 'mtg_' prefix
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Timing
    scheduled_start TIMESTAMP,
    scheduled_end TIMESTAMP,
    actual_start TIMESTAMP,
    actual_end TIMESTAMP,
    duration_minutes FLOAT,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, transcribing, analyzing, completed, failed
    error_message TEXT,
    
    -- File info
    file_path VARCHAR(500),
    file_size_bytes BIGINT,
    audio_format VARCHAR(50),
    
    -- Integration
    project_id VARCHAR(50), -- Link to PM project
    created_by UUID REFERENCES users(id) ON DELETE SET NULL, -- MCP User
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE INDEX idx_meetings_status ON meetings(status);
CREATE INDEX idx_meetings_project_id ON meetings(project_id);
CREATE INDEX idx_meetings_created_by ON meetings(created_by);

-- Participants table
CREATE TABLE IF NOT EXISTS meeting_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id VARCHAR(50) NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    role VARCHAR(50) DEFAULT 'participant', -- host, presenter, participant, guest
    speaking_time_seconds FLOAT,
    pm_user_id VARCHAR(255), -- Link to PM system user
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_meeting_participants_meeting_id ON meeting_participants(meeting_id);

-- Transcripts table
CREATE TABLE IF NOT EXISTS transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id VARCHAR(50) NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    language VARCHAR(10) DEFAULT 'en',
    full_text TEXT,
    word_count INT,
    duration_seconds FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_transcripts_meeting_id ON transcripts(meeting_id);

-- Transcript Segments table
CREATE TABLE IF NOT EXISTS transcript_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcript_id UUID NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    segment_index INT NOT NULL,
    speaker VARCHAR(255),
    speaker_id UUID REFERENCES meeting_participants(id) ON DELETE SET NULL,
    text TEXT NOT NULL,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    confidence FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transcript_segments_transcript_id ON transcript_segments(transcript_id);
CREATE INDEX idx_transcript_segments_time ON transcript_segments(transcript_id, start_time);

-- Action Items table (extracted from meeting)
CREATE TABLE IF NOT EXISTS meeting_action_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id VARCHAR(50) NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed
    
    assignee_name VARCHAR(255),
    assignee_id UUID REFERENCES meeting_participants(id) ON DELETE SET NULL,
    due_date TIMESTAMP,
    
    pm_task_id VARCHAR(255), -- ID of created task in PM system
    original_text VARCHAR(500), -- Source text from transcript
    
    confidence_score FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_meeting_action_items_meeting_id ON meeting_action_items(meeting_id);
CREATE INDEX idx_meeting_action_items_status ON meeting_action_items(status);

-- Decisions table
CREATE TABLE IF NOT EXISTS meeting_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id VARCHAR(50) NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    context TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_meeting_decisions_meeting_id ON meeting_decisions(meeting_id);

-- Meeting Summary table
CREATE TABLE IF NOT EXISTS meeting_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id VARCHAR(50) NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    summary_type VARCHAR(50) DEFAULT 'executive', -- executive, detailed, key_points
    content TEXT NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_meeting_summaries_meeting_id ON meeting_summaries(meeting_id);

-- Update timestamp triggers
CREATE TRIGGER update_meetings_updated_at BEFORE UPDATE ON meetings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_meeting_action_items_updated_at BEFORE UPDATE ON meeting_action_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
