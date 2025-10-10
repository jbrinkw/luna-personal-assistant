/**
 * Automation Memory Backend Server
 * Express API for managing memories, flows, and schedules
 */
const express = require('express');
const cors = require('cors');
const path = require('path');

// Load environment
require('dotenv').config({ path: path.resolve(__dirname, '../../../.env') });

const db = require('./db');

const app = express();
app.use(cors());
app.use(express.json());

// Health check
app.get('/healthz', (req, res) => {
  res.json({ status: 'ok' });
});

// Task Flows CRUD
app.get('/api/task_flows', async (req, res) => {
  try {
    const rows = await db.listFlows();
    res.json(rows || []);
  } catch (e) {
    console.error('[task_flows] GET error:', e);
    res.status(500).json({ error: String(e) });
  }
});

app.post('/api/task_flows', async (req, res) => {
  try {
    const { call_name, prompts, agent } = req.body || {};
    const id = await db.createFlow(
      String(call_name || 'new_flow'),
      Array.isArray(prompts) ? prompts : [],
      String(agent || 'simple_agent')
    );
    res.json({ id });
  } catch (e) {
    console.error('[task_flows] POST error:', e);
    res.status(500).json({ error: String(e) });
  }
});

app.put('/api/task_flows/:id', async (req, res) => {
  try {
    const ok = await db.updateFlow(Number(req.params.id), req.body || {});
    res.json({ ok });
  } catch (e) {
    console.error('[task_flows] PUT error:', e);
    res.status(500).json({ error: String(e) });
  }
});

app.delete('/api/task_flows/:id', async (req, res) => {
  try {
    await db.deleteFlow(Number(req.params.id));
    res.json({ ok: true });
  } catch (e) {
    console.error('[task_flows] DELETE error:', e);
    res.status(500).json({ error: String(e) });
  }
});

// Run a flow (placeholder - actual execution would use prompt_runner)
app.post('/api/task_flows/:id/run', async (req, res) => {
  try {
    const id = Number(req.params.id);
    const flow = await db.getFlow(id);
    if (!flow) return res.status(404).json({ error: 'not found' });
    
    // TODO: Execute flow using Python prompt_runner
    console.log(`[runner] Would run flow: ${flow.call_name} with agent: ${flow.agent}`);
    
    res.json({ ok: true, status: 'completed', id });
  } catch (e) {
    console.error('[task_flows] RUN error:', e);
    res.status(500).json({ error: String(e) });
  }
});

// Scheduled Prompts CRUD
app.get('/api/scheduled_prompts', async (req, res) => {
  try {
    const rows = await db.listSchedules();
    res.json(rows || []);
  } catch (e) {
    console.error('[scheduled_prompts] GET error:', e);
    res.status(500).json({ error: String(e) });
  }
});

app.post('/api/scheduled_prompts', async (req, res) => {
  try {
    const { time_of_day, days_of_week, prompt, agent, enabled } = req.body || {};
    const id = await db.createSchedule(
      String(time_of_day || '09:00'),
      Array.isArray(days_of_week) ? days_of_week : [false, false, false, false, false, false, false],
      String(prompt || ''),
      String(agent || 'simple_agent'),
      !!enabled
    );
    res.json({ id });
  } catch (e) {
    console.error('[scheduled_prompts] POST error:', e);
    res.status(500).json({ error: String(e) });
  }
});

app.put('/api/scheduled_prompts/:id', async (req, res) => {
  try {
    const ok = await db.updateSchedule(Number(req.params.id), req.body || {});
    res.json({ ok });
  } catch (e) {
    console.error('[scheduled_prompts] PUT error:', e);
    res.status(500).json({ error: String(e) });
  }
});

app.delete('/api/scheduled_prompts/:id', async (req, res) => {
  try {
    await db.deleteSchedule(Number(req.params.id));
    res.json({ ok: true });
  } catch (e) {
    console.error('[scheduled_prompts] DELETE error:', e);
    res.status(500).json({ error: String(e) });
  }
});

// Memories CRUD
app.get('/api/memories', async (req, res) => {
  try {
    const rows = await db.listMemories();
    res.json(rows || []);
  } catch (e) {
    console.error('[memories] GET error:', e);
    res.status(500).json({ error: String(e) });
  }
});

app.post('/api/memories', async (req, res) => {
  try {
    const { content } = req.body || {};
    const id = await db.createMemory(String(content || ''));
    res.json({ id });
  } catch (e) {
    console.error('[memories] POST error:', e);
    res.status(500).json({ error: String(e) });
  }
});

app.put('/api/memories/:id', async (req, res) => {
  try {
    const { content } = req.body || {};
    await db.updateMemory(Number(req.params.id), String(content || ''));
    res.json({ ok: true });
  } catch (e) {
    console.error('[memories] PUT error:', e);
    res.status(500).json({ error: String(e) });
  }
});

app.delete('/api/memories/:id', async (req, res) => {
  try {
    await db.deleteMemory(Number(req.params.id));
    res.json({ ok: true });
  } catch (e) {
    console.error('[memories] DELETE error:', e);
    res.status(500).json({ error: String(e) });
  }
});

// Get available agents from Agent API
app.get('/api/agents', async (req, res) => {
  try {
    const agentApiUrl = `http://127.0.0.1:${process.env.AGENT_API_PORT || 8080}/v1/models`;
    const response = await fetch(agentApiUrl);
    const data = await response.json();
    const agents = (data.data || []).map(m => m.id);
    res.json({ agents });
  } catch (e) {
    console.error('[agents] GET error:', e);
    // Return default agents if Agent API not available
    res.json({ agents: ['simple_agent', 'passthrough_agent'] });
  }
});

const PORT = process.env.AM_API_PORT || 3051;
app.listen(PORT, '127.0.0.1', () => {
  console.log(`[automation-memory] API listening on http://127.0.0.1:${PORT}`);
  console.log(`[automation-memory] Database: ${process.env.DB_NAME || 'luna'}`);
});

