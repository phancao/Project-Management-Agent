-- AI Provider API Keys
-- Stores API keys for different AI/LLM providers (OpenAI, Anthropic, Google, etc.)

CREATE TABLE IF NOT EXISTS ai_provider_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id VARCHAR(50) NOT NULL, -- 'openai', 'anthropic', 'google', etc.
    provider_name VARCHAR(255) NOT NULL,
    api_key VARCHAR(1000), -- Encrypted or plain (depending on security requirements)
    base_url VARCHAR(500), -- Optional custom base URL
    model_name VARCHAR(255), -- Optional default model
    additional_config JSONB, -- Additional provider-specific config
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider_id) -- One API key per provider
);

-- Trigger to update updated_at
CREATE TRIGGER update_ai_provider_api_keys_updated_at BEFORE UPDATE ON ai_provider_api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

