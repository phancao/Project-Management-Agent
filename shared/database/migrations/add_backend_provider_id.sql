-- Migration: Add backend_provider_id column to pm_provider_connections table
-- This column is used to map backend provider IDs to PM Service provider IDs

-- Add the column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'pm_provider_connections' 
        AND column_name = 'backend_provider_id'
    ) THEN
        ALTER TABLE pm_provider_connections 
        ADD COLUMN backend_provider_id UUID UNIQUE;
        
        COMMENT ON COLUMN pm_provider_connections.backend_provider_id IS 
            'Backend provider ID - used to map backend provider IDs to PM Service provider IDs';
    END IF;
END $$;

