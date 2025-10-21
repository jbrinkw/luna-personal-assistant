#!/usr/bin/env node
/**
 * Monitor incoming requests to the backend API
 * Run this to see if the UI is actually making requests
 */

const path = require('path');
const express = require('express');
const cors = require('cors');

require('dotenv').config({ path: path.resolve(__dirname, '../../../.env') });

const db = require('./db');

const app = express();
app.use(cors());
app.use(express.json());

// Request logging middleware
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${req.method} ${req.path} - Origin: ${req.headers.origin || 'none'}`);
  next();
});

// Health check
app.get('/healthz', (req, res) => {
  console.log('  → Responding with status: ok');
  res.json({ status: 'ok' });
});

// Task Flows CRUD
app.get('/api/task_flows', async (req, res) => {
  try {
    const rows = await db.listFlows();
    console.log(`  → Returning ${rows.length} flows`);
    res.json(rows || []);
  } catch (e) {
    console.error('  → ERROR:', e.message);
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
    console.log(`  → Created flow with id: ${id}`);
    res.json({ id });
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

app.put('/api/task_flows/:id', async (req, res) => {
  try {
    const ok = await db.updateFlow(Number(req.params.id), req.body || {});
    console.log(`  → Updated flow ${req.params.id}`);
    res.json({ ok });
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

app.delete('/api/task_flows/:id', async (req, res) => {
  try {
    await db.deleteFlow(Number(req.params.id));
    console.log(`  → Deleted flow ${req.params.id}`);
    res.json({ ok: true });
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

app.post('/api/task_flows/:id/run', async (req, res) => {
  try {
    const id = Number(req.params.id);
    const flow = await db.getFlow(id);
    if (!flow) return res.status(404).json({ error: 'not found' });
    
    console.log(`  → Running flow: ${flow.call_name}`);
    res.json({ ok: true, status: 'completed', id });
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

// Scheduled Prompts CRUD
app.get('/api/scheduled_prompts', async (req, res) => {
  try {
    const rows = await db.listSchedules();
    console.log(`  → Returning ${rows.length} schedules`);
    res.json(rows || []);
  } catch (e) {
    console.error('  → ERROR:', e.message);
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
    console.log(`  → Created schedule with id: ${id}`);
    res.json({ id });
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

app.put('/api/scheduled_prompts/:id', async (req, res) => {
  try {
    const ok = await db.updateSchedule(Number(req.params.id), req.body || {});
    console.log(`  → Updated schedule ${req.params.id}`);
    res.json({ ok });
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

app.delete('/api/scheduled_prompts/:id', async (req, res) => {
  try {
    await db.deleteSchedule(Number(req.params.id));
    console.log(`  → Deleted schedule ${req.params.id}`);
    res.json({ ok: true });
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

// Memories CRUD
app.get('/api/memories', async (req, res) => {
  try {
    const rows = await db.listMemories();
    console.log(`  → Returning ${rows.length} memories`);
    res.json(rows || []);
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

app.post('/api/memories', async (req, res) => {
  try {
    const { content } = req.body || {};
    const id = await db.createMemory(String(content || ''));
    console.log(`  → Created memory with id: ${id}`);
    res.json({ id });
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

app.put('/api/memories/:id', async (req, res) => {
  try {
    const { content } = req.body || {};
    await db.updateMemory(Number(req.params.id), String(content || ''));
    console.log(`  → Updated memory ${req.params.id}`);
    res.json({ ok: true });
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

app.delete('/api/memories/:id', async (req, res) => {
  try {
    await db.deleteMemory(Number(req.params.id));
    console.log(`  → Deleted memory ${req.params.id}`);
    res.json({ ok: true });
  } catch (e) {
    console.error('  → ERROR:', e.message);
    res.status(500).json({ error: String(e) });
  }
});

// Get available agents from Agent API
app.get('/api/agents', async (req, res) => {
  try {
    const getApiHost = () => {
      // Try environment variable first, fallback to detecting host
      return process.env.AGENT_API_HOST || (typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1');
    };
    const agentApiUrl = `http://${getApiHost()}:${process.env.AGENT_API_PORT || 8080}/v1/models`;
    const response = await fetch(agentApiUrl);
    const data = await response.json();
    const agents = (data.data || []).map(m => m.id);
    console.log(`  → Returning ${agents.length} agents`);
    res.json({ agents });
  } catch (e) {
    console.error('  → ERROR (using defaults):', e.message);
    res.json({ agents: ['simple_agent', 'passthrough_agent'] });
  }
});

const PORT = process.env.AM_API_PORT || 3051;

console.log('\n' + '='.repeat(60));
console.log('🔍 AUTOMATION MEMORY - REQUEST MONITOR');
console.log('='.repeat(60));
console.log(`\nListening on http://0.0.0.0:${PORT}`);
console.log('Watching for incoming requests...\n');
console.log('If you see NO requests while the UI is open,');
console.log('the UI might be cached or using the wrong URL.\n');
console.log('Press Ctrl+C to stop.\n');
console.log('='.repeat(60) + '\n');

app.listen(PORT, '0.0.0.0', () => {
  console.log(`✓ Server ready - waiting for requests...`);
});




