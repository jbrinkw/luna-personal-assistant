/* eslint-disable */
const express = require('express');
const path = require('path');
// Load environment variables from .env file in project root
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });
const { spawn } = require('child_process');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Debug: Log environment variables
console.log('Debug - Environment variables:');
console.log('GROCY_BASE_URL:', process.env.GROCY_BASE_URL ? 'SET' : 'NOT SET');
console.log('GROCY_API_KEY:', process.env.GROCY_API_KEY ? 'SET' : 'NOT SET');
console.log('OPENAI_API_KEY:', process.env.OPENAI_API_KEY ? 'SET' : 'NOT SET');

// In-memory queue and job store (MVP)
const jobStore = new Map(); // jobId -> { id, status, op, barcode, logs: [], result }
let nextJobId = 1;

// Simple FIFO queue; one worker at a time
const queue = [];
let isWorking = false;

// Recent newly created items (max 3)
const recentNewItems = []; // [{ product_id, name, barcode, best_before_date, location_id, location_label, booking_id }]
// Modification logs (last 50)
const modificationLogs = [];

// Location discovery/cache
let locationMap = null; // { label->id }
let locationIdToLabel = null; // { id->label }

async function ensureLocationMap() {
  if (locationMap && locationIdToLabel) return;
  const baseUrl = process.env.GROCY_BASE_URL;
  const apiKey = process.env.GROCY_API_KEY;
  if (!baseUrl || !apiKey) return; // silently skip if not configured
  try {
    const res = await grocyFetch('GET', '/objects/locations');
    const rows = Array.isArray(res) ? res : (res && Array.isArray(res.data) ? res.data : []);
    const labelToId = {};
    const idToLabel = {};
    const synonyms = {
      fridge: ['fridge', 'refrigerator', 'refrig'],
      freezer: ['freezer'],
      pantry: ['pantry', 'cupboard', 'larder'],
    };
    rows.forEach((row) => {
      const id = Number(row && row.id);
      const name = (row && row.name || '').toString().toLowerCase();
      if (!Number.isFinite(id) || !name) return;
      Object.keys(synonyms).forEach((label) => {
        const words = synonyms[label];
        if (words.some((w) => name === w || name.includes(w))) {
          if (labelToId[label] == null) labelToId[label] = id;
          idToLabel[id] = label;
        }
      });
    });
    locationMap = labelToId;
    locationIdToLabel = idToLabel;
  } catch (e) {
    // ignore
  }
}

async function grocyFetch(method, path_, body) {
  const baseUrl = (process.env.GROCY_BASE_URL || '').replace(/\/$/, '');
  const apiKey = process.env.GROCY_API_KEY;
  if (!baseUrl || !apiKey) throw new Error('GROCY_BASE_URL and GROCY_API_KEY are required on the server');
  const url = baseUrl + path_;
  const init = {
    method,
    headers: { 'GROCY-API-KEY': apiKey, 'Accept': 'application/json' },
  };
  if (body) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const res = await fetch(url, init);
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} - ${text}`);
  try { return JSON.parse(text); } catch { return text; }
}

function enqueueJob(op, barcode) {
  const id = String(nextJobId++);
  const job = { id, status: 'queued', op, barcode, logs: [], result: null };
  jobStore.set(id, job);
  queue.push(job);
  pumpQueue();
  return job;
}

function pumpQueue() {
  if (isWorking) return;
  const job = queue.shift();
  if (!job) return;
  isWorking = true;
  job.status = 'processing';
  // Use local JS processor when available so the web folder is standalone
  runLocalProcessor(job)
    .catch((err) => {
      job.logs.push(`[error] ${String(err && err.message || err)}`);
      job.result = { status: 'error', message: String(err && err.message || err), barcode: job.barcode, operation: job.op };
      job.status = 'done';
    })
    .finally(() => {
      isWorking = false;
      setImmediate(pumpQueue);
    });
}

async function runLocalProcessor(job) {
  try {
    const { run } = require('./processor');
    const result = await run(job.op, job.barcode);
    // attach logs from processor (if any)
    try { const logs = (run && run.lastLogs) || []; logs.forEach((l) => job.logs.push(l)); } catch {}
    job.result = result || { status: 'error', message: 'no result' };

    // Mirror Python path: capture recent items for newly created products and then mark job done
    const postTasks = [];
    try {
      if (job.result && job.result.created_product) {
        // Try to parse AI suggestion for original location_label
        let aiLocationLabel = null;
        try {
          const aiLine = findLastData(job.logs, 'ai.suggestion');
          if (aiLine) {
            const aiJson = aiLine.substring(aiLine.indexOf(':') + 1).trim();
            const ai = JSON.parse(aiJson);
            if (ai && typeof ai.location_label === 'string') aiLocationLabel = ai.location_label.toLowerCase();
          }
        } catch (_) {}

        const line = findLastData(job.logs, 'grocy.add_by_barcode.response');
        if (line) {
          const jsonStr = line.substring(line.indexOf(':') + 1).trim();
          const arr = JSON.parse(jsonStr);
          const entry = Array.isArray(arr) && arr.length > 0 ? arr[0] : null;
          if (entry) {
            const booking_id = Number(entry.id);
            const product_id = Number(entry.product_id);
            const best_before_date = entry.best_before_date;
            const location_id = Number(entry.location_id);
            const nameFromResult = job.result && job.result.product_name || undefined;
            const pushItem = async () => {
              const name = nameFromResult || (await grocyFetch('GET', `/objects/products/${product_id}`)).name;
              await ensureLocationMap();
              const location_label = aiLocationLabel || (locationIdToLabel && locationIdToLabel[location_id]) || undefined;
              recentNewItems.unshift({ product_id, name, barcode: job.barcode, best_before_date, location_id, location_label, booking_id });
              while (recentNewItems.length > 3) recentNewItems.pop();
            };
            postTasks.push(pushItem().catch(() => {}));
          }
        } else {
          // Minimal fallback for create without add log
          postTasks.push(
            Promise.resolve().then(() => {
              recentNewItems.unshift({
                product_id: job.result.product_id,
                name: job.result.product_name,
                barcode: job.result.barcode || job.barcode,
                best_before_date: null,
                location_id: null,
                location_label: null,
                booking_id: null,
              });
              while (recentNewItems.length > 3) recentNewItems.pop();
            })
          );
        }
      }
    } catch (_) {
      // ignore
    }
    await Promise.allSettled(postTasks);
    job.status = 'done';
  } catch (e) {
    // Fallback to Python runner if local processor is unavailable
    await runPythonJob(job);
  }
}

function runPythonJob(job) {
  return new Promise((resolve) => {
    const args = ['-m', 'grocy_pig.single_item_processor', '--op', job.op, '--barcode', job.barcode];
    const proc = spawn('python', args, {
      cwd: path.join(__dirname, '..', '..'), // project root (folder with package)
      env: process.env,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    proc.stdout.on('data', (chunk) => {
      const text = chunk.toString();
      text.split(/\r?\n/).forEach((line) => {
        if (!line) return;
        job.logs.push(line);
      });
    });
    proc.stderr.on('data', (chunk) => {
      const text = chunk.toString();
      text.split(/\r?\n/).forEach((line) => {
        if (!line) return;
        job.logs.push(`[stderr] ${line}`);
      });
    });
    proc.on('close', () => {
      // The processor prints a final JSON line; try to parse last JSON-looking line
      const jsonLine = findLastJson(job.logs);
      if (jsonLine) {
        try {
          job.result = JSON.parse(jsonLine);
        } catch (e) {
          job.result = { status: 'error', message: 'Invalid JSON from processor', raw: jsonLine };
        }
      } else {
        job.result = { status: 'error', message: 'No JSON result from processor', logs: job.logs.slice(-5) };
      }
      // Only capture recent items for newly created products
      const postTasks = [];
      try {
        if (job.result && job.result.created_product) {
          // Try to parse AI suggestion for original location_label
          let aiLocationLabel = null;
          try {
            const aiLine = findLastData(job.logs, 'ai.suggestion');
            if (aiLine) {
              const aiJson = aiLine.substring(aiLine.indexOf(':') + 1).trim();
              const ai = JSON.parse(aiJson);
              if (ai && typeof ai.location_label === 'string') aiLocationLabel = ai.location_label.toLowerCase();
            }
          } catch (_) {}

          const line = findLastData(job.logs, 'grocy.add_by_barcode.response');
          if (line) {
            const jsonStr = line.substring(line.indexOf(':') + 1).trim();
            const arr = JSON.parse(jsonStr);
            const entry = Array.isArray(arr) && arr.length > 0 ? arr[0] : null;
            if (entry) {
              const booking_id = Number(entry.id);
              const product_id = Number(entry.product_id);
              const best_before_date = entry.best_before_date;
              const location_id = Number(entry.location_id);
              const nameFromResult = job.result && job.result.product_name || undefined;
              const pushItem = async () => {
                const name = nameFromResult || (await grocyFetch('GET', `/objects/products/${product_id}`)).name;
                await ensureLocationMap();
                const location_label = aiLocationLabel || (locationIdToLabel && locationIdToLabel[location_id]) || undefined;
                recentNewItems.unshift({ product_id, name, barcode: job.barcode, best_before_date, location_id, location_label, booking_id });
                while (recentNewItems.length > 3) recentNewItems.pop();
              };
              postTasks.push(pushItem().catch(() => {}));
            }
          } else {
            // Minimal fallback for create without add log
            postTasks.push(
              Promise.resolve().then(() => {
                recentNewItems.unshift({
                  product_id: job.result.product_id,
                  name: job.result.product_name,
                  barcode: job.result.barcode || job.barcode,
                  best_before_date: null,
                  location_id: null,
                  location_label: null,
                  booking_id: null,
                });
                while (recentNewItems.length > 3) recentNewItems.pop();
              })
            );
          }
        }
      } catch (_) {
        // ignore
      }
      Promise.allSettled(postTasks).finally(() => {
        job.status = 'done';
        resolve();
      });
    });
  });
}

function findLastJson(lines) {
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i].trim();
    if (!line) continue;
    if (line.startsWith('{') && line.endsWith('}')) return line;
  }
  return null;
}

function findLastData(lines, label) {
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i];
    if (line && line.startsWith('[data] ') && line.includes(label + ':')) return line;
  }
  return null;
}

// Routes
app.post('/api/scan/add', (req, res) => {
  const barcode = String(req.body && req.body.barcode || '').trim();
  if (!barcode) return res.status(400).json({ error: 'barcode required' });
  const job = enqueueJob('add', barcode);
  res.json({ jobId: job.id });
});

app.post('/api/scan/remove', (req, res) => {
  const barcode = String(req.body && req.body.barcode || '').trim();
  if (!barcode) return res.status(400).json({ error: 'barcode required' });
  const job = enqueueJob('remove', barcode);
  res.json({ jobId: job.id });
});

app.get('/api/jobs/:id', (req, res) => {
  const job = jobStore.get(String(req.params.id));
  if (!job) return res.status(404).json({ error: 'not found' });
  // Light logs: only keep [step] lines and the final JSON result
  const minimalLogs = (job.logs || []).filter((l) => l && l.startsWith('[step] '));
  res.json({ id: job.id, status: job.status, logs: minimalLogs, result: job.result });
});

// Recent new items
app.get('/api/recent-new-items', async (req, res) => {
  await ensureLocationMap();
  res.json(recentNewItems.map((it) => ({
    product_id: it.product_id,
    name: it.name,
    barcode: it.barcode,
    best_before_date: it.best_before_date,
    location_id: it.location_id,
    location_label: it.location_label || (locationIdToLabel && locationIdToLabel[it.location_id]) || null,
    booking_id: it.booking_id,
  })));
});

// Recent modification logs
app.get('/api/mod-logs', (req, res) => {
  res.json(modificationLogs);
});

// Minimal proxy endpoints for test script
// Use regex route to capture everything after /api/proxy/
app.all(/^\/api\/proxy\/(.*)$/i, async (req, res) => {
  try {
    const match = req.url.match(/^\/api\/proxy\/(.*)$/i);
    const sub = (match && match[1]) || '';
    const method = req.method;
    const body = (req.body && Object.keys(req.body).length > 0) ? req.body : undefined;
    const result = await grocyFetch(method, '/' + sub, body);
    res.json(result);
  } catch (e) {
    res.status(400).json({ error: String(e && e.message || e) });
  }
});

// Delete a product by barcode: zero inventory, delete barcode rows, delete product
app.delete('/api/products/by-barcode/:barcode', async (req, res) => {
  try {
    const barcode = String(req.params.barcode || '').trim();
    if (!barcode) return res.status(400).json({ error: 'barcode required' });
    // Find mappings
    const barRes = await grocyFetch('GET', '/objects/product_barcodes');
    const rows = Array.isArray(barRes) ? barRes : (barRes && Array.isArray(barRes.data) ? barRes.data : []);
    const targets = rows.filter((r) => r && String(r.barcode) === barcode);
    let deleted = 0;
    for (const row of targets) {
      const pid = Number(row.product_id);
      try { await grocyFetch('POST', `/stock/products/${pid}/inventory`, { new_amount: 0 }); } catch (_) {}
      try { await grocyFetch('DELETE', `/objects/product_barcodes/${row.id}`); } catch (_) {}
      try { await grocyFetch('DELETE', `/objects/products/${pid}`); deleted++; } catch (_) {}
    }
    res.json({ status: 'ok', deleted });
  } catch (e) {
    res.status(400).json({ error: String(e && e.message || e) });
  }
});

// Inline edit: name, best_before_days (int) or best_before_date, location (via label or id)
app.patch('/api/recent-new-items/:productId', async (req, res) => {
  try {
    await ensureLocationMap();
    const pid = Number(req.params.productId);
    if (!Number.isFinite(pid)) return res.status(400).json({ error: 'invalid productId' });
    const item = recentNewItems.find((x) => x.product_id === pid);
    if (!item) return res.status(404).json({ error: 'not found' });

    const updates = req.body || {};
    const changed = await recreateProductAndInventory(item, updates);
    try {
      modificationLogs.unshift({
        ts: new Date().toISOString(),
        type: 'recreate',
        barcode: item.barcode,
        old_product_id: pid,
        new_product_id: changed && changed.product_id,
        name: changed && changed.name,
        location_label: changed && changed.location_label,
        restocked_amount: changed && changed.restocked_amount,
      });
      while (modificationLogs.length > 50) modificationLogs.pop();
    } catch (_) {}
    res.json({ status: 'ok', changed });
  } catch (e) {
    try {
      const pid = Number(req.params.productId);
      modificationLogs.unshift({
        ts: new Date().toISOString(),
        type: 'error',
        product_id: Number.isFinite(pid) ? pid : null,
        error: String(e && e.message || e),
      });
      while (modificationLogs.length > 50) modificationLogs.pop();
    } catch (_) {}
    res.status(400).json({ error: String(e && e.message || e) });
  }
});

function daysFromNow(targetDateStr) {
  try {
    const now = new Date();
    const t = new Date(targetDateStr);
    const ms = t.getTime() - now.getTime();
    const days = Math.floor(ms / (1000 * 60 * 60 * 24));
    return days > 0 ? days : 0;
  } catch (_) {
    return null;
  }
}

function dateStringFromDays(days) {
  try {
    const d = new Date();
    d.setDate(d.getDate() + Number(days || 0));
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  } catch (_) {
    return null;
  }
}

async function recreateProductAndInventory(item, updates) {
  // Preconditions
  const pid = Number(item.product_id);
  const barcode = item.barcode;
  if (!barcode) throw new Error('Recent item missing barcode');

  // Read original product and quantity
  const original = await grocyFetch('GET', `/objects/products/${pid}`);
  if (!original || !Number.isFinite(Number(original.qu_id_purchase)) || !Number.isFinite(Number(original.qu_id_stock))) {
    throw new Error('Original product missing required unit ids');
  }
  const stockInfo = await grocyFetch('GET', `/stock/products/${pid}`);
  const amount = Number(stockInfo && (stockInfo.stock_amount ?? stockInfo.amount ?? 0));
  if (!Number.isFinite(amount)) throw new Error('Failed to read current quantity');

  // Determine desired fields
  const desiredName = (typeof updates.name === 'string' && updates.name.trim()) ? updates.name.trim() : (item.name || original.name);
  let desiredLocationId = Number(original.location_id);
  if (typeof updates.location_label === 'string') {
    const label = updates.location_label.toLowerCase();
    const mapped = locationMap && locationMap[label];
    if (!Number.isFinite(mapped)) throw new Error('Unknown location label: ' + updates.location_label);
    desiredLocationId = Number(mapped);
  }
  let desiredDefaultBbd = Number(original.default_best_before_days || 0);
  if (Number.isFinite(Number(updates.best_before_days))) desiredDefaultBbd = Number(updates.best_before_days);

  // Delete root product
  await grocyFetch('DELETE', `/objects/products/${pid}`);

  // Re-create root product
  const createPayload = {
    name: desiredName,
    location_id: desiredLocationId,
    qu_id_purchase: Number(original.qu_id_purchase),
    qu_id_stock: Number(original.qu_id_stock),
  };
  if (Number.isFinite(desiredDefaultBbd) && desiredDefaultBbd > 0) createPayload.default_best_before_days = desiredDefaultBbd;
  const created = await grocyFetch('POST', '/objects/products', createPayload);
  const newPid = Number((created && (created.created_object_id || created.id)) || 0);
  if (!Number.isFinite(newPid) || newPid <= 0) throw new Error('Failed to create product');

  // Re-link barcode and re-add quantity
  await grocyFetch('POST', '/objects/product_barcodes', { product_id: newPid, barcode });
  if (amount > 0) {
    const addPayload = { amount };
    if (Number.isFinite(desiredDefaultBbd) && desiredDefaultBbd > 0) {
      const dateStr = dateStringFromDays(desiredDefaultBbd);
      if (dateStr) addPayload.best_before_date = dateStr;
    }
    await grocyFetch('POST', `/stock/products/${newPid}/add`, addPayload);
  }

  // Update memory
  item.product_id = newPid;
  item.name = desiredName;
  item.location_id = desiredLocationId;
  item.location_label = (locationIdToLabel && locationIdToLabel[desiredLocationId]) || item.location_label;
  if (Number.isFinite(desiredDefaultBbd) && desiredDefaultBbd > 0) item.best_before_date = dateStringFromDays(desiredDefaultBbd);

  return {
    product_id: item.product_id,
    name: item.name,
    location_id: item.location_id,
    location_label: item.location_label,
    best_before_date: item.best_before_date || null,
    restocked_amount: amount,
  };
}

const PORT = process.env.GROCY_IO_WIZ_PORT || 3100;
app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  const hasBase = !!process.env.GROCY_BASE_URL;
  const hasKey = !!process.env.GROCY_API_KEY;
  console.log(`Server listening on http://localhost:${PORT}`);
  console.log(`Grocy env detected -> BASE_URL: ${hasBase} API_KEY: ${hasKey}`);
});


