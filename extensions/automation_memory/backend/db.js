/**
 * Database module for automation_memory - Postgres
 */
const { Pool } = require('pg');
const path = require('path');

// Load environment from project root
const envPath = path.resolve(__dirname, '../../../.env');
require('dotenv').config({ path: envPath });

// Ensure password is always a string (pg library requirement)
// Check both DB_PASSWORD and PGPASSWORD, ensuring we get a string value
let dbPassword = process.env.DB_PASSWORD;
if (!dbPassword || typeof dbPassword !== 'string') {
  dbPassword = process.env.PGPASSWORD;
}
if (!dbPassword || typeof dbPassword !== 'string') {
  dbPassword = '';
}
// Explicitly convert to string to satisfy pg library
dbPassword = String(dbPassword);

const dbHost = process.env.DB_HOST || process.env.PGHOST || process.env.POSTGRES_HOST || '127.0.0.1';
const dbPort = Number(process.env.DB_PORT || process.env.PGPORT || 5432);
const dbName = process.env.DB_NAME || process.env.PGDATABASE || 'luna';
const dbUser = process.env.DB_USER || process.env.PGUSER || 'postgres';

// Debug logging
console.log('[automation-memory] DB config:', {
  host: dbHost,
  port: dbPort,
  database: dbName,
  user: dbUser,
  password_set: !!dbPassword && dbPassword !== '',
  password_type: typeof dbPassword,
  password_length: dbPassword.length,
  DB_PASSWORD_env: process.env.DB_PASSWORD ? 'SET' : 'NOT SET',
  PGPASSWORD_env: process.env.PGPASSWORD ? 'SET' : 'NOT SET'
});

const pool = new Pool({
  host: dbHost,
  port: dbPort,
  database: dbName,
  user: dbUser,
  password: dbPassword,
});

// Task Flows
async function listFlows() {
  const result = await pool.query('SELECT id, call_name, prompts, agent FROM task_flows ORDER BY id DESC');
  return result.rows.map(row => ({
    ...row,
    prompts: typeof row.prompts === 'string' ? JSON.parse(row.prompts) : row.prompts
  }));
}

async function getFlow(id) {
  const result = await pool.query('SELECT id, call_name, prompts, agent FROM task_flows WHERE id = $1', [id]);
  const row = result.rows[0];
  if (!row) return null;
  return {
    ...row,
    prompts: typeof row.prompts === 'string' ? JSON.parse(row.prompts) : row.prompts
  };
}

async function getFlowByName(callName) {
  const result = await pool.query('SELECT id, call_name, prompts, agent FROM task_flows WHERE call_name = $1', [callName]);
  const row = result.rows[0];
  if (!row) return null;
  return {
    ...row,
    prompts: typeof row.prompts === 'string' ? JSON.parse(row.prompts) : row.prompts
  };
}

async function createFlow(callName, prompts, agent = 'simple_agent') {
  const result = await pool.query(
    'INSERT INTO task_flows (call_name, prompts, agent, created_at, updated_at) VALUES ($1, $2, $3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id',
    [callName, JSON.stringify(prompts || []), agent]
  );
  return result.rows[0].id;
}

async function updateFlow(id, fields) {
  const current = await getFlow(id);
  if (!current) return false;

  const updates = {
    call_name: typeof fields.call_name === 'string' ? fields.call_name : current.call_name,
    prompts: Array.isArray(fields.prompts) ? fields.prompts : current.prompts,
    agent: typeof fields.agent === 'string' ? fields.agent : current.agent,
  };

  await pool.query(
    'UPDATE task_flows SET call_name = $1, prompts = $2, agent = $3, updated_at = CURRENT_TIMESTAMP WHERE id = $4',
    [updates.call_name, JSON.stringify(updates.prompts), updates.agent, id]
  );
  return true;
}

async function deleteFlow(id) {
  await pool.query('DELETE FROM task_flows WHERE id = $1', [id]);
}

// Scheduled Prompts
async function listSchedules() {
  const result = await pool.query('SELECT id, time_of_day, days_of_week, prompt, agent, enabled FROM scheduled_prompts ORDER BY id DESC');
  return result.rows.map(row => ({
    ...row,
    days_of_week: typeof row.days_of_week === 'string' ? JSON.parse(row.days_of_week) : row.days_of_week
  }));
}

async function getSchedule(id) {
  const result = await pool.query('SELECT id, time_of_day, days_of_week, prompt, agent, enabled FROM scheduled_prompts WHERE id = $1', [id]);
  const row = result.rows[0];
  if (!row) return null;
  return {
    ...row,
    days_of_week: typeof row.days_of_week === 'string' ? JSON.parse(row.days_of_week) : row.days_of_week
  };
}

async function createSchedule(timeOfDay, daysOfWeek, prompt, agent = 'simple_agent', enabled = true) {
  const result = await pool.query(
    'INSERT INTO scheduled_prompts (time_of_day, days_of_week, prompt, agent, enabled, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id',
    [timeOfDay, JSON.stringify(daysOfWeek || []), prompt, agent, enabled]
  );
  return result.rows[0].id;
}

async function updateSchedule(id, fields) {
  const current = await getSchedule(id);
  if (!current) return false;

  const updates = {
    time_of_day: typeof fields.time_of_day === 'string' ? fields.time_of_day : current.time_of_day,
    days_of_week: Array.isArray(fields.days_of_week) ? fields.days_of_week : current.days_of_week,
    prompt: typeof fields.prompt === 'string' ? fields.prompt : current.prompt,
    agent: typeof fields.agent === 'string' ? fields.agent : current.agent,
    enabled: typeof fields.enabled === 'boolean' ? fields.enabled : current.enabled,
  };

  await pool.query(
    'UPDATE scheduled_prompts SET time_of_day = $1, days_of_week = $2, prompt = $3, agent = $4, enabled = $5, updated_at = CURRENT_TIMESTAMP WHERE id = $6',
    [updates.time_of_day, JSON.stringify(updates.days_of_week), updates.prompt, updates.agent, updates.enabled, id]
  );
  return true;
}

async function deleteSchedule(id) {
  await pool.query('DELETE FROM scheduled_prompts WHERE id = $1', [id]);
}

// Memories
async function listMemories() {
  const result = await pool.query('SELECT id, content FROM memories ORDER BY id DESC');
  return result.rows;
}

async function createMemory(content) {
  const result = await pool.query(
    'INSERT INTO memories (content, created_at, updated_at) VALUES ($1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id',
    [content]
  );
  return result.rows[0].id;
}

async function updateMemory(id, content) {
  await pool.query('UPDATE memories SET content = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2', [content, id]);
}

async function deleteMemory(id) {
  await pool.query('DELETE FROM memories WHERE id = $1', [id]);
}

// Flow Executions
async function createExecution(flowId, totalPrompts) {
  const result = await pool.query(
    'INSERT INTO flow_executions (flow_id, total_prompts, status, started_at) VALUES ($1, $2, $3, CURRENT_TIMESTAMP) RETURNING id',
    [flowId, totalPrompts, 'running']
  );
  return result.rows[0].id;
}

async function getExecution(id) {
  const result = await pool.query(
    'SELECT id, flow_id, status, current_prompt_index, total_prompts, started_at, completed_at, error, prompt_results FROM flow_executions WHERE id = $1',
    [id]
  );
  const row = result.rows[0];
  if (!row) return null;
  return {
    ...row,
    prompt_results: typeof row.prompt_results === 'string' ? JSON.parse(row.prompt_results) : row.prompt_results
  };
}

async function listActiveExecutions() {
  const result = await pool.query(
    `SELECT e.id, e.flow_id, e.status, e.current_prompt_index, e.total_prompts, e.started_at, e.completed_at, e.error, e.prompt_results,
            f.call_name, f.agent, f.prompts
     FROM flow_executions e
     JOIN task_flows f ON e.flow_id = f.id
     WHERE e.status = 'running'
     ORDER BY e.started_at DESC`
  );
  return result.rows.map(row => ({
    ...row,
    prompt_results: typeof row.prompt_results === 'string' ? JSON.parse(row.prompt_results) : row.prompt_results,
    prompts: typeof row.prompts === 'string' ? JSON.parse(row.prompts) : row.prompts
  }));
}

async function listRecentExecutions(limit = 20) {
  const result = await pool.query(
    `SELECT e.id, e.flow_id, e.status, e.current_prompt_index, e.total_prompts, e.started_at, e.completed_at, e.error, e.prompt_results,
            f.call_name, f.agent
     FROM flow_executions e
     JOIN task_flows f ON e.flow_id = f.id
     ORDER BY e.started_at DESC
     LIMIT $1`,
    [limit]
  );
  return result.rows.map(row => ({
    ...row,
    prompt_results: typeof row.prompt_results === 'string' ? JSON.parse(row.prompt_results) : row.prompt_results
  }));
}

async function updateExecutionProgress(id, promptIndex, promptResult) {
  const execution = await getExecution(id);
  if (!execution) return false;

  const results = Array.isArray(execution.prompt_results) ? execution.prompt_results : [];
  results.push(promptResult);

  await pool.query(
    'UPDATE flow_executions SET current_prompt_index = $1, prompt_results = $2 WHERE id = $3',
    [promptIndex, JSON.stringify(results), id]
  );
  return true;
}

async function completeExecution(id, status = 'completed', error = null) {
  await pool.query(
    'UPDATE flow_executions SET status = $1, completed_at = CURRENT_TIMESTAMP, error = $2 WHERE id = $3',
    [status, error, id]
  );
}

module.exports = {
  pool,  // Export pool for schema initialization
  listFlows,
  getFlow,
  getFlowByName,
  createFlow,
  updateFlow,
  deleteFlow,
  listSchedules,
  getSchedule,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  listMemories,
  createMemory,
  updateMemory,
  deleteMemory,
  createExecution,
  getExecution,
  listActiveExecutions,
  listRecentExecutions,
  updateExecutionProgress,
  completeExecution,
};

