-- Migration: Add user_mcp_api_keys table for MCP Server authentication
-- Created: 2025-01-20
-- Purpose: Allow external clients (Cursor, VS Code, etc.) to authenticate
--          and identify users when connecting to MCP Server

-- User API Keys for MCP Server access
CREATE TABLE IF NOT EXISTS user_mcp_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    api_key VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),  -- Optional: "Cursor", "VS Code", "Windsurf", etc.
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,  -- Optional: for key expiration
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_mcp_api_keys_user_id ON user_mcp_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_mcp_api_keys_api_key ON user_mcp_api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_user_mcp_api_keys_active ON user_mcp_api_keys(is_active) WHERE is_active = TRUE;

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_user_mcp_api_keys_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_mcp_api_keys_updated_at
    BEFORE UPDATE ON user_mcp_api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_user_mcp_api_keys_updated_at();

-- Comments
COMMENT ON TABLE user_mcp_api_keys IS 'API keys for external MCP clients to authenticate and identify users';
COMMENT ON COLUMN user_mcp_api_keys.api_key IS 'Unique API key (format: mcp_xxx)';
COMMENT ON COLUMN user_mcp_api_keys.name IS 'Optional name for the key (e.g., "Cursor Desktop", "VS Code")';
COMMENT ON COLUMN user_mcp_api_keys.last_used_at IS 'Timestamp of last API key usage';
COMMENT ON COLUMN user_mcp_api_keys.expires_at IS 'Optional expiration date for the key';

