/**
 * Database module for automation_memory - Postgres
 */
const { Pool } = require('pg');
const path = require('path');

// Load environment from project root
require('dotenv').config({ path: path.resolve(__dirname, '../../../.env') });

const pool = new Pool({
  host: process.env.DB_HOST || process.env.PGHOST || '127.0.0.1',
  port: Number(process.env.DB_PORT || process.env.PGPORT || 5432),
  database: process.env.DB_NAME || process.env.PGDATABASE || 'luna',
  user: process.env.DB_USER || process.env.PGUSER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.PGPASSWORD || '',
});

// Task Flows
async function listFlows() {
  const result = await pool.query('SELECT id, call_name, prompts, agent FROM task_flows ORDER BY id DESC');
  return result.rows;
}

async function getFlow(id) {
  const result = await pool.query('SELECT id, call_name, prompts, agent FROM task_flows WHERE id = $1', [id]);
  return result.rows[0] || null;
}

async function getFlowByName(callName) {
  const result = await pool.query('SELECT id, call_name, prompts, agent FROM task_flows WHERE call_name = $1', [callName]);
  return result.rows[0] || null;
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
  return result.rows;
}

async function getSchedule(id) {
  const result = await pool.query('SELECT id, time_of_day, days_of_week, prompt, agent, enabled FROM scheduled_prompts WHERE id = $1', [id]);
  return result.rows[0] || null;
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

module.exports = {
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
};

