-- Seed PM Provider Connections
-- This script adds OpenProject and JIRA providers to the database

-- First, ensure we have a user to use as created_by (use the admin user)
DO $$
DECLARE
    admin_user_id UUID;
BEGIN
    -- Get or create admin user
    SELECT id INTO admin_user_id FROM users WHERE email = 'admin@example.com' LIMIT 1;
    
    IF admin_user_id IS NULL THEN
        INSERT INTO users (email, name, role) 
        VALUES ('admin@example.com', 'System Administrator', 'admin')
        RETURNING id INTO admin_user_id;
    END IF;
    
    -- Insert OpenProject provider if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pm_provider_connections WHERE name = 'OpenProject Local' AND provider_type = 'openproject') THEN
        INSERT INTO pm_provider_connections (
            name, 
            provider_type, 
            base_url, 
            api_key, 
            is_active,
            created_by
        ) VALUES (
            'OpenProject Local',
            'openproject',
            'http://localhost:8080',
            'YOUR_OPENPROJECT_API_KEY_HERE', -- Replace with your actual OpenProject API key
            true,
            admin_user_id
        );
        RAISE NOTICE 'OpenProject provider added';
    ELSE
        RAISE NOTICE 'OpenProject provider already exists';
    END IF;
    
    -- Insert JIRA provider if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pm_provider_connections WHERE name = 'JIRA Cloud' AND provider_type = 'jira') THEN
        INSERT INTO pm_provider_connections (
            name, 
            provider_type, 
            base_url, 
            api_token, 
            username,
            is_active,
            created_by
        ) VALUES (
            'JIRA Cloud',
            'jira',
            'https://phancao1984.atlassian.net',
            'YOUR_ATLASSIAN_API_TOKEN_HERE', -- Replace with your actual Atlassian API token
            'your-email@example.com', -- Update this with your actual JIRA account email
            true,
            admin_user_id
        );
        RAISE NOTICE 'JIRA provider added';
    ELSE
        RAISE NOTICE 'JIRA provider already exists';
    END IF;
END $$;

