-- MCP Server Independent Database Schema
-- This database is completely separate from the backend system
-- PostgreSQL database for PM MCP Server

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (for MCP Server only)
-- Users who connect via MCP clients (Cursor, VS Code, etc.)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User MCP API Keys (for authenticating MCP clients)
CREATE TABLE user_mcp_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    api_key VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),  -- Optional: "Cursor", "VS Code", etc.
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,  -- Optional: for key expiration
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_mcp_api_keys_user_id ON user_mcp_api_keys(user_id);
CREATE INDEX idx_user_mcp_api_keys_api_key ON user_mcp_api_keys(api_key);

-- PM Provider connections (for external PM system integration)
-- Each user can have multiple provider connections (JIRA, OpenProject, etc.)
CREATE TABLE pm_provider_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    provider_type VARCHAR(50) NOT NULL, -- 'openproject', 'jira', 'clickup', etc.
    base_url VARCHAR(500) NOT NULL,
    api_key VARCHAR(500),
    api_token VARCHAR(500),
    username VARCHAR(255),
    organization_id VARCHAR(255),
    project_key VARCHAR(255),
    workspace_id VARCHAR(255),
    additional_config JSONB,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync_at TIMESTAMP
);

CREATE INDEX idx_pm_provider_connections_created_by ON pm_provider_connections(created_by);
CREATE INDEX idx_pm_provider_connections_provider_type ON pm_provider_connections(provider_type);
CREATE INDEX idx_pm_provider_connections_is_active ON pm_provider_connections(is_active);

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_mcp_api_keys_updated_at BEFORE UPDATE ON user_mcp_api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pm_provider_connections_updated_at BEFORE UPDATE ON pm_provider_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();









