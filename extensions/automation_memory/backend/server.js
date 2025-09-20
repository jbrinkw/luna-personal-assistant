const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../../../.env') });
require('dotenv').config();

const db = require('./db/index');
const scheduler = require('./scheduler/index');
const { spawn } = require('child_process');

const app = express();
app.use(cors());
app.use(express.json());

// Ensure DB schema initialized before starting scheduler
Promise.resolve(db.init())
  .then(() => {
    try { scheduler.start(); } catch (_) {}
  })
  .catch((e) => {
    console.error('[init] db init failed', e);
    try { scheduler.start(); } catch (_) {}
  });

function regenTools() {
  try {
    const script = path.resolve(__dirname, '../autogen_tools.py');
    const py = spawn('python', [script], { cwd: path.resolve(__dirname, '../../..') });
    py.on('error', (e) => console.error('[autogen] spawn error', e));
  } catch (e) {
    console.error('[autogen] error', e);
  }
}

// Task Flows CRUD
app.get('/api/task_flows', async (req, res) => {
  try { const rows = await db.listFlows(); res.json(rows || []); } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.post('/api/task_flows', async (req, res) => {
  try {
    const { call_name, prompts } = req.body || {};
    const id = await db.createFlow(String(call_name || 'new_flow'), Array.isArray(prompts) ? prompts : []);
    regenTools();
    res.json({ id });
  } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.put('/api/task_flows/:id', async (req, res) => {
  try { const ok = await db.updateFlow(Number(req.params.id), req.body || {}); regenTools(); res.json({ ok }); } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.delete('/api/task_flows/:id', async (req, res) => {
  try { await db.deleteFlow(Number(req.params.id)); regenTools(); res.json({ ok: true }); } catch (e) { res.status(500).json({ error: String(e) }); }
});

// Run a flow now (uses Python runner later)
app.post('/api/task_flows/:id/run', async (req, res) => {
  try {
    const id = Number(req.params.id);
    const flow = await db.getFlow(id);
    if (!flow) return res.status(404).json({ error: 'not found' });
    const runner = path.resolve(__dirname, 'services/flow_runner/run_flow.py');
    const args = ['python', runner, String(flow.call_name || ''), JSON.stringify(flow.prompts || [])];
    const proc = spawn(args[0], args.slice(1), { cwd: path.resolve(__dirname, '../../..') });
    let out = '';
    let err = '';
    proc.stdout.on('data', (d) => { try { out += String(d); } catch (_) {} });
    proc.stderr.on('data', (d) => { try { err += String(d); } catch (_) {} });
    proc.on('close', (code) => {
      if (code === 0) {
        res.json({ ok: true, status: 'completed', id, output: (out || '').trim() });
      } else {
        res.status(500).json({ ok: false, status: 'error', id, error: (err || '').trim() });
      }
    });
  } catch (e) { res.status(500).json({ error: String(e) }); }
});

// Scheduled Prompts CRUD
app.get('/api/scheduled_prompts', async (req, res) => {
  try { const rows = await db.listSchedules(); res.json(rows || []); } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.post('/api/scheduled_prompts', async (req, res) => {
  try {
    const { time_of_day, days_of_week, prompt, enabled } = req.body || {};
    const id = await db.createSchedule(String(time_of_day || '09:00'), Array.isArray(days_of_week) ? days_of_week : [false,false,false,false,false,false,false], String(prompt || ''), !!enabled);
    res.json({ id });
  } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.put('/api/scheduled_prompts/:id', async (req, res) => {
  try { const ok = await db.updateSchedule(Number(req.params.id), req.body || {}); res.json({ ok }); } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.delete('/api/scheduled_prompts/:id', async (req, res) => {
  try { await db.deleteSchedule(Number(req.params.id)); res.json({ ok: true }); } catch (e) { res.status(500).json({ error: String(e) }); }
});

// Memories CRUD
app.get('/api/memories', async (req, res) => {
  try { const rows = await db.listMemories(); res.json(rows || []); } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.post('/api/memories', async (req, res) => {
  try { const { content } = req.body || {}; const id = await db.createMemory(String(content || '')); res.json({ id }); } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.put('/api/memories/:id', async (req, res) => {
  try { const { content } = req.body || {}; await db.updateMemory(Number(req.params.id), String(content || '')); res.json({ ok: true }); } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.delete('/api/memories/:id', async (req, res) => {
  try { await db.deleteMemory(Number(req.params.id)); res.json({ ok: true }); } catch (e) { res.status(500).json({ error: String(e) }); }
});

// Queued Messages CRUD
app.get('/api/queued_messages', async (req, res) => {
  try { const rows = await db.listQueued(); res.json(rows || []); } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.post('/api/queued_messages', async (req, res) => {
  try { const { content } = req.body || {}; const id = await db.createQueued(String(content || '')); res.json({ id }); } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.put('/api/queued_messages/:id', async (req, res) => {
  try { const { content } = req.body || {}; await db.updateQueued(Number(req.params.id), String(content || '')); res.json({ ok: true }); } catch (e) { res.status(500).json({ error: String(e) }); }
});
app.delete('/api/queued_messages/:id', async (req, res) => {
  try { await db.deleteQueued(Number(req.params.id)); res.json({ ok: true }); } catch (e) { res.status(500).json({ error: String(e) }); }
});

const PORT = process.env.AM_API_PORT || 3051;
app.listen(PORT, () => {
  console.log(`[automation-memory] API on ${PORT}, db=${db.dbPath}`);
});


