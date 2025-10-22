-- Automation Memory Database Schema
-- Tables for memories, task flows, scheduled prompts, and flow executions

-- Memories table
CREATE TABLE IF NOT EXISTS memories (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Task Flows table
CREATE TABLE IF NOT EXISTS task_flows (
  id SERIAL PRIMARY KEY,
  call_name VARCHAR(255) NOT NULL,
  prompts TEXT NOT NULL,  -- JSON array stored as text
  agent VARCHAR(100) NOT NULL DEFAULT 'simple_agent',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Scheduled Prompts table
CREATE TABLE IF NOT EXISTS scheduled_prompts (
  id SERIAL PRIMARY KEY,
  time_of_day VARCHAR(10) NOT NULL,  -- Format: "HH:MM"
  days_of_week TEXT NOT NULL,  -- JSON array stored as text
  prompt TEXT NOT NULL,
  agent VARCHAR(100) NOT NULL DEFAULT 'simple_agent',
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Flow Executions table
CREATE TABLE IF NOT EXISTS flow_executions (
  id SERIAL PRIMARY KEY,
  flow_id INTEGER NOT NULL REFERENCES task_flows(id) ON DELETE CASCADE,
  total_prompts INTEGER NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'running',  -- 'running', 'completed', 'failed'
  current_prompt_index INTEGER DEFAULT 0,
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  error TEXT,
  prompt_results TEXT  -- JSON array stored as text
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_flow_executions_flow_id ON flow_executions(flow_id);
CREATE INDEX IF NOT EXISTS idx_flow_executions_status ON flow_executions(status);
CREATE INDEX IF NOT EXISTS idx_flow_executions_started_at ON flow_executions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_flows_call_name ON task_flows(call_name);
CREATE INDEX IF NOT EXISTS idx_scheduled_prompts_enabled ON scheduled_prompts(enabled);

