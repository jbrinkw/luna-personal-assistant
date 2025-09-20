const { Pool } = require('pg');
const path = require('path');

const pool = new Pool({
  host: process.env.AM_DB_HOST || process.env.DB_HOST || process.env.PGHOST || '127.0.0.1',
  port: Number(process.env.AM_DB_PORT || process.env.DB_PORT || process.env.PGPORT || 5432),
  database: process.env.AM_DB_NAME || process.env.DB_NAME || process.env.PGDATABASE || 'automation_memory',
  user: process.env.AM_DB_USER || process.env.DB_USER || process.env.PGUSER || 'postgres',
  password: process.env.AM_DB_PASSWORD || process.env.DB_PASSWORD || process.env.PGPASSWORD || '',
});

async function init() {
  const client = await pool.connect();
  try {
    await client.query(`
      CREATE TABLE IF NOT EXISTS task_flows (
        id SERIAL PRIMARY KEY,
        call_name TEXT UNIQUE NOT NULL,
        prompts JSONB NOT NULL DEFAULT '[]',
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
      );
      CREATE TABLE IF NOT EXISTS scheduled_prompts (
        id SERIAL PRIMARY KEY,
        time_of_day TEXT NOT NULL,
        days_of_week JSONB NOT NULL DEFAULT '[]',
        prompt TEXT NOT NULL,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
      );
      CREATE TABLE IF NOT EXISTS memories (
        id SERIAL PRIMARY KEY,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
      );
      CREATE TABLE IF NOT EXISTS queued_messages (
        id SERIAL PRIMARY KEY,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
      );
    `);
  } finally {
    client.release();
  }
}

function nowIso() { return new Date().toISOString(); }

// Task Flows
function listFlows() {
  return pool.query('SELECT id, call_name, prompts FROM task_flows ORDER BY id DESC').then(r => r.rows);
}
function getFlow(id) {
  return pool.query('SELECT id, call_name, prompts FROM task_flows WHERE id = $1', [id]).then(r => r.rows[0] || null);
}
function getFlowByName(call_name) {
  return pool.query('SELECT id, call_name, prompts FROM task_flows WHERE call_name = $1', [call_name]).then(r => r.rows[0] || null);
}
function createFlow(call_name, prompts) {
  return pool.query('INSERT INTO task_flows (call_name, prompts, created_at, updated_at) VALUES ($1, $2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id', [call_name, JSON.stringify(prompts || [])]).then(r => r.rows[0].id);
}
function updateFlow(id, fields) {
  return getFlow(id).then(cur => {
    if (!cur) return false;
    const next = {
      call_name: typeof fields.call_name === 'string' ? fields.call_name : cur.call_name,
      prompts: Array.isArray(fields.prompts) ? fields.prompts : cur.prompts,
    };
    return pool.query('UPDATE task_flows SET call_name = $1, prompts = $2, updated_at = CURRENT_TIMESTAMP WHERE id = $3', [next.call_name, JSON.stringify(next.prompts), id]).then(() => true);
  });
}
function deleteFlow(id) {
  return pool.query('DELETE FROM task_flows WHERE id = $1', [id]);
}

// Scheduled Prompts
function listSchedules() {
  return pool.query('SELECT id, time_of_day, days_of_week, prompt, enabled FROM scheduled_prompts ORDER BY id DESC').then(r => r.rows);
}
function getSchedule(id) {
  return pool.query('SELECT id, time_of_day, days_of_week, prompt, enabled FROM scheduled_prompts WHERE id = $1', [id]).then(r => r.rows[0] || null);
}
function createSchedule(time_of_day, days_of_week, prompt, enabled) {
  return pool.query('INSERT INTO scheduled_prompts (time_of_day, days_of_week, prompt, enabled, created_at, updated_at) VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id', [String(time_of_day || ''), JSON.stringify(days_of_week || []), String(prompt || ''), !!enabled]).then(r => r.rows[0].id);
}
function updateSchedule(id, fields) {
  return getSchedule(id).then(cur => {
    if (!cur) return false;
    const next = {
      time_of_day: typeof fields.time_of_day === 'string' ? fields.time_of_day : cur.time_of_day,
      days_of_week: Array.isArray(fields.days_of_week) ? fields.days_of_week : cur.days_of_week,
      prompt: typeof fields.prompt === 'string' ? fields.prompt : cur.prompt,
      enabled: typeof fields.enabled === 'boolean' ? fields.enabled : cur.enabled,
    };
    return pool.query('UPDATE scheduled_prompts SET time_of_day = $1, days_of_week = $2, prompt = $3, enabled = $4, updated_at = CURRENT_TIMESTAMP WHERE id = $5', [String(next.time_of_day), JSON.stringify(next.days_of_week), String(next.prompt), !!next.enabled, id]).then(() => true);
  });
}
function deleteSchedule(id) {
  return pool.query('DELETE FROM scheduled_prompts WHERE id = $1', [id]);
}

// Memories
function listMemories() { return pool.query('SELECT id, content FROM memories ORDER BY id DESC').then(r => r.rows); }
function createMemory(content) { return pool.query('INSERT INTO memories (content, created_at, updated_at) VALUES ($1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id', [String(content || '')]).then(r => r.rows[0].id); }
function updateMemory(id, content) { return pool.query('UPDATE memories SET content = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2', [String(content || ''), id]); }
function deleteMemory(id) { return pool.query('DELETE FROM memories WHERE id = $1', [id]); }

// Queued Messages
function listQueued() { return pool.query('SELECT id, content, created_at FROM queued_messages ORDER BY id DESC').then(r => r.rows); }
function createQueued(content) { return pool.query('INSERT INTO queued_messages (content, created_at) VALUES ($1, CURRENT_TIMESTAMP) RETURNING id', [String(content || '')]).then(r => r.rows[0].id); }
function updateQueued(id, content) { return pool.query('UPDATE queued_messages SET content = $1 WHERE id = $2', [String(content || ''), id]); }
function deleteQueued(id) { return pool.query('DELETE FROM queued_messages WHERE id = $1', [id]); }

module.exports = {
  dbPath: path.resolve(__dirname, '../db/automation_memory.sqlite'),
  init,
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
  listQueued,
  createQueued,
  updateQueued,
  deleteQueued,
};