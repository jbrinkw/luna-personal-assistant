/**
 * Automation Memory Backend Server
 * Express API for managing memories, flows, and schedules
 */
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

// Load environment
require('dotenv').config({ path: path.resolve(__dirname, '../../../.env') });

const db = require('./db');

const app = express();
app.use(cors());
app.use(express.json());

// In-memory cache for flow executions (persists while server runs)
const executionCache = {
  active: new Map(),    // execution_id -> execution data
  recent: [],           // array of recent executions (max 50)
  maxRecent: 50
};

// Helper to update cache
function updateExecutionCache(execution) {
  if (execution.status === 'running') {
    executionCache.active.set(execution.id, execution);
  } else {
    // Move from active to recent
    executionCache.active.delete(execution.id);
    
    // Add to recent if not already there
    const existingIndex = executionCache.recent.findIndex(e => e.id === execution.id);
    if (existingIndex >= 0) {
      executionCache.recent[existingIndex] = execution;
    } else {
      executionCache.recent.unshift(execution);
      // Keep only max recent
      if (executionCache.recent.length > executionCache.maxRecent) {
        executionCache.recent.pop();
      }
    }
  }
}

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

// Run a flow
app.post('/api/task_flows/:id/run', async (req, res) => {
  try {
    const flowId = Number(req.params.id);
    const flow = await db.getFlow(flowId);
    if (!flow) return res.status(404).json({ error: 'not found' });
    
    const prompts = Array.isArray(flow.prompts) ? flow.prompts : JSON.parse(flow.prompts || '[]');
    
    // Create execution record
    const executionId = await db.createExecution(flowId, prompts.length);
    
    // Add to cache immediately
    const newExecution = {
      id: executionId,
      flow_id: flowId,
      status: 'running',
      current_prompt_index: 0,
      total_prompts: prompts.length,
      started_at: new Date().toISOString(),
      completed_at: null,
      error: null,
      prompt_results: [],
      call_name: flow.call_name,
      agent: flow.agent,
      prompts: prompts
    };
    updateExecutionCache(newExecution);
    
    // Start flow execution in background
    const { spawn } = require('child_process');
    const runnerPath = path.join(__dirname, 'flow_runner.py');
    
    // Use venv Python if available, otherwise fall back to system python3
    const venvPython = path.resolve(__dirname, '../../../.venv/bin/python3');
    const pythonCmd = require('fs').existsSync(venvPython) ? venvPython : (process.env.PYTHON_CMD || 'python3');
    
    const runner = spawn(pythonCmd, [runnerPath, String(flowId), String(executionId)], {
      detached: true,
      stdio: 'ignore',
    });
    
    runner.unref(); // Allow parent to exit independently
    
    console.log(`[runner] Started flow execution: ${flow.call_name} (execution_id: ${executionId})`);
    
    res.json({ ok: true, execution_id: executionId, flow_id: flowId });
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

// Flow Executions - Get active executions (from cache)
app.get('/api/executions/active', async (req, res) => {
  try {
    // Refresh cache from database for running executions
    const dbExecutions = await db.listActiveExecutions();
    dbExecutions.forEach(exec => updateExecutionCache(exec));
    
    // Return from cache
    const activeExecutions = Array.from(executionCache.active.values());
    res.json(activeExecutions);
  } catch (e) {
    console.error('[executions] GET active error:', e);
    res.status(500).json({ error: String(e) });
  }
});

// Flow Executions - Get recent executions (from cache + database)
app.get('/api/executions/recent', async (req, res) => {
  try {
    const limit = Number(req.query.limit) || 20;
    
    // If cache is empty, populate from database
    if (executionCache.recent.length === 0) {
      const dbExecutions = await db.listRecentExecutions(limit);
      dbExecutions.forEach(exec => updateExecutionCache(exec));
    }
    
    // Return from cache
    res.json(executionCache.recent.slice(0, limit));
  } catch (e) {
    console.error('[executions] GET recent error:', e);
    res.status(500).json({ error: String(e) });
  }
});

// Flow Executions - Refresh cache (polls database for updates)
app.get('/api/executions/refresh', async (req, res) => {
  try {
    // Get all running executions from DB and update cache
    const activeExecs = await db.listActiveExecutions();
    
    // Check each active execution for updates
    for (const exec of activeExecs) {
      const cached = executionCache.active.get(exec.id);
      // Update if new or if progress changed
      if (!cached || cached.current_prompt_index !== exec.current_prompt_index || 
          JSON.stringify(cached.prompt_results) !== JSON.stringify(exec.prompt_results)) {
        updateExecutionCache(exec);
      }
    }
    
    // Check if any cached active executions completed
    for (const [id, cached] of executionCache.active.entries()) {
      const stillRunning = activeExecs.find(e => e.id === id);
      if (!stillRunning) {
        // Execution completed, fetch final state from DB
        const finalExec = await db.getExecution(id);
        if (finalExec) {
          // Fetch flow details to include call_name and agent
          const flow = await db.getFlow(finalExec.flow_id);
          if (flow) {
            finalExec.call_name = flow.call_name;
            finalExec.agent = flow.agent;
          }
          updateExecutionCache(finalExec);
        }
      }
    }
    
    res.json({ 
      active: Array.from(executionCache.active.values()),
      recent: executionCache.recent.slice(0, 20)
    });
  } catch (e) {
    console.error('[executions] REFRESH error:', e);
    res.status(500).json({ error: String(e) });
  }
});

// Flow Executions - Get specific execution
app.get('/api/executions/:id', async (req, res) => {
  try {
    const execution = await db.getExecution(Number(req.params.id));
    if (!execution) {
      return res.status(404).json({ error: 'execution not found' });
    }
    res.json(execution);
  } catch (e) {
    console.error('[executions] GET error:', e);
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
    res.json({ agents });
  } catch (e) {
    console.error('[agents] GET error:', e);
    // Return default agents if Agent API not available
    res.json({ agents: ['simple_agent', 'passthrough_agent'] });
  }
});

// Database initialization - auto-create tables if missing
async function initializeSchema() {
  try {
    // Check if memories table exists
    const result = await db.pool.query(
      `SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'memories'
      );`
    );
    
    if (!result.rows[0].exists) {
      console.log('[automation-memory] Tables missing, initializing schema...');
      
      // Read and execute schema.sql
      const schemaPath = path.resolve(__dirname, '../schema.sql');
      const schemaSQL = fs.readFileSync(schemaPath, 'utf8');
      await db.pool.query(schemaSQL);
      
      console.log('[automation-memory] Database schema initialized successfully');
    }
  } catch (error) {
    console.error('[automation-memory] Schema initialization error (non-fatal):', error.message);
    // Continue anyway - tables might exist but check failed
  }
}

// Start server after initializing schema
const PORT = process.env.AM_API_PORT || 5302;

initializeSchema().then(() => {
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[automation-memory] API listening on 0.0.0.0:${PORT}`);
    console.log(`[automation-memory] Database: ${process.env.DB_NAME || 'luna'}`);
    console.log(`[automation-memory] Port dynamically assigned by supervisor`);
  });
}).catch(err => {
  console.error('[automation-memory] Failed to start:', err);
  process.exit(1);
});

