-- BugBase Database Schema
-- PostgreSQL schema for bug tracking

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Bugs table
CREATE TABLE IF NOT EXISTS bugs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    screenshot_path VARCHAR(500),
    navigation_history JSONB,
    page_url VARCHAR(500),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comments table
CREATE TABLE IF NOT EXISTS bug_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bug_id UUID REFERENCES bugs(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    author VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bugs_status ON bugs(status);
CREATE INDEX IF NOT EXISTS idx_bugs_severity ON bugs(severity);
CREATE INDEX IF NOT EXISTS idx_bugs_created_at ON bugs(created_at);
CREATE INDEX IF NOT EXISTS idx_bug_comments_bug_id ON bug_comments(bug_id);

-- Updated trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to bugs table
DROP TRIGGER IF EXISTS update_bugs_updated_at ON bugs;
CREATE TRIGGER update_bugs_updated_at
    BEFORE UPDATE ON bugs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
