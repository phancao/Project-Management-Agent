-- Sprints table for sprint planning
CREATE TABLE IF NOT EXISTS sprints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    duration_weeks INTEGER,
    duration_days INTEGER,
    capacity_hours DECIMAL(10,2),
    planned_hours DECIMAL(10,2),
    utilization DECIMAL(5,2), -- percentage
    status VARCHAR(50) DEFAULT 'planned', -- planned, in_progress, completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sprint tasks junction table
CREATE TABLE IF NOT EXISTS sprint_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sprint_id UUID REFERENCES sprints(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    assigned_to_name VARCHAR(255), -- Store team member name
    capacity_used DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sprint_id, task_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sprints_project_id ON sprints(project_id);
CREATE INDEX IF NOT EXISTS idx_sprints_status ON sprints(status);
CREATE INDEX IF NOT EXISTS idx_sprint_tasks_sprint_id ON sprint_tasks(sprint_id);
CREATE INDEX IF NOT EXISTS idx_sprint_tasks_task_id ON sprint_tasks(task_id);

-- Trigger for updated_at
CREATE TRIGGER update_sprints_updated_at BEFORE UPDATE ON sprints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

