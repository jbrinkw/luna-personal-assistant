/* eslint-disable */
const http = require('http');
const https = require('https');
const path = require('path');
// Load env from repo root .env only
try { require('dotenv').config({ path: path.join(__dirname, '..', '..', '..', '.env') }); } catch (_) {}

const BASE = (process.env.GROCY_BASE_URL || '').replace(/\/$/, '');
const KEY = process.env.GROCY_API_KEY || '';
const OFF_BASE = process.env.OPENFOODFACTS_BASE_URL || 'https://world.openfoodfacts.org';
const OPENAI_MODEL = process.env.OPENAI_MODEL || 'gpt-4.1';

function dateStringFromDays(days) {
  const d = new Date();
  d.setDate(d.getDate() + Number(days || 0));
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

async function fetchJson(method, path, body) {
  if (!BASE || !KEY) throw new Error('GROCY_BASE_URL and GROCY_API_KEY are required on the server');
  const url = new URL(BASE + path);
  const isHttps = url.protocol === 'https:';
  const data = body ? Buffer.from(JSON.stringify(body)) : null;
  const opts = {
    method,
    hostname: url.hostname,
    port: url.port || (isHttps ? 443 : 80),
    path: url.pathname + (url.search || ''),
    headers: { 'GROCY-API-KEY': KEY, 'Accept': 'application/json' },
  };
  if (data) { opts.headers['Content-Type'] = 'application/json'; opts.headers['Content-Length'] = data.length; }
  const mod = isHttps ? https : http;
  return new Promise((resolve, reject) => {
    const req = mod.request(opts, (res) => {
      let text = '';
      res.on('data', (c) => (text += c.toString()));
      res.on('end', () => {
        if (res.statusCode < 200 || res.statusCode >= 300) {
          return reject(new Error(`${res.statusCode} ${res.statusMessage} - ${text}`));
        }
        try { resolve(JSON.parse(text)); } catch { resolve(text); }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

async function processAdd(barcode, logs) {
  const step = (m) => logs.push(`[step] ${m}`);
  const data = (k, v) => { try { logs.push(`[data] ${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`); } catch {} };

  step(`Operation: add | barcode: ${barcode}`);
  step('Checking Grocy for existing product by barcode ...');
  let byb = null;
  try { byb = await fetchJson('GET', `/stock/products/by-barcode/${barcode}`); } catch (e) {
    const msg = String(e || '');
    if (!(msg.includes(' 400 ') || msg.includes(' 404 '))) throw e;
  }
  if (byb) {
    data('grocy.by_barcode.existing', byb);
    step('Found existing product; adding amount 1 via /add ...');
    const r = await fetchJson('POST', `/stock/products/by-barcode/${barcode}/add`, { amount: 1 });
    data('grocy.add_by_barcode.response', r);
    return { status: 'ok', message: 'Added 1 to existing product by barcode', barcode, operation: 'add', created_product: false, added_amount: 1 };
  }

  step('Not found in Grocy; querying OpenFoodFacts ...');
  const off = await new Promise((resolve) => {
    https.get(`${OFF_BASE}/api/v2/product/${encodeURIComponent(barcode)}.json`, (res) => {
      let t=''; res.on('data',c=>t+=c); res.on('end',()=>{ try{ resolve(JSON.parse(t)); } catch{ resolve({}); } });
    }).on('error', () => resolve({}));
  });
  const offName = off && off.product && off.product.product_name ? String(off.product.product_name).trim() : '';
  if (!offName) throw new Error('OpenFoodFacts had no usable name for this barcode');

  step('Calling AI to select location and shelf-life ...');
  const OpenAI = require('openai');
  const client = new OpenAI.OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const sys = 'You are selecting storage and shelf-life for a grocery product. If its for the freezer defualt to 180 days. Return STRICT JSON only: {"location_label":"fridge|freezer|pantry","default_best_before_days":integer>=0}.';
  const human = `Product name: ${JSON.stringify(offName)}\nOpenFoodFacts attributes: ${JSON.stringify({ name: offName })}`;
  const aiResp = await client.chat.completions.create({ model: OPENAI_MODEL, temperature: 0, messages: [{ role: 'system', content: sys }, { role: 'user', content: human }] });
  const text = aiResp && aiResp.choices && aiResp.choices[0] && aiResp.choices[0].message && aiResp.choices[0].message.content || '';
  let ai; try { ai = JSON.parse(text); } catch { throw new Error('LLM output did not match schema'); }
  data('ai.suggestion', ai);

  step('Discovering Grocy location IDs (fridge/freezer/pantry) ...');
  const locs = await fetchJson('GET', '/objects/locations');
  const rows = Array.isArray(locs) ? locs : (locs && locs.data) || [];
  let locId = null; const label = String(ai.location_label).toLowerCase();
  for (const r of rows) { const nm = String(r && r.name || '').toLowerCase(); if (nm===label || nm.includes(label)) { locId = Number(r.id); break; } }
  if (!Number.isFinite(Number(locId))) throw new Error(`Could not resolve location id for '${ai.location_label}'`);
  data('grocy.location_id', { [label]: locId });

  // Choose a quantity unit id (piece/first)
  const qu = await fetchJson('GET', '/objects/quantity_units');
  const qrows = Array.isArray(qu) ? qu : (qu && qu.data) || [];
  let quId = null;
  for (const r of qrows) { const nm = String(r && r.name || '').toLowerCase(); if (['piece','pcs','unit','units'].includes(nm)) { quId = Number(r.id); break; } }
  if (!Number.isFinite(Number(quId)) && qrows[0]) quId = Number(qrows[0].id);
  if (!Number.isFinite(Number(quId))) throw new Error('No quantity unit ids returned by Grocy');

  step('Creating product in Grocy via /objects/products ...');
  const payload = { name: offName, location_id: Number(locId), qu_id_purchase: Number(quId), qu_id_stock: Number(quId), default_best_before_days: Number(ai.default_best_before_days) };
  data('grocy.create_product.payload', payload);
  const created = await fetchJson('POST', '/objects/products', payload);
  const pid = Number((created && (created.created_object_id || created.id)) || 0);
  data('grocy.create_product.response', created);
  if (!Number.isFinite(pid) || pid <= 0) throw new Error('Product creation did not return an id');

  step('Linking barcode to product via /objects/product_barcodes ...');
  const link = await fetchJson('POST', '/objects/product_barcodes', { product_id: pid, barcode });
  data('grocy.link_barcode.response', link);
  step('Adding amount 1 via /stock/products/by-barcode/{barcode}/add ...');
  const add = await fetchJson('POST', `/stock/products/by-barcode/${barcode}/add`, { amount: 1 });
  data('grocy.add_by_barcode.response', add);
  return { status: 'ok', message: 'Created new product from OFF + AI and added 1', barcode, operation: 'add', product_id: pid, product_name: offName, created_product: true, added_amount: 1 };
}

async function processRemove(barcode, logs) {
  const step = (m) => logs.push(`[step] ${m}`);
  const data = (k, v) => { try { logs.push(`[data] ${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`); } catch {} };
  step(`Operation: remove | barcode: ${barcode}`);
  step('Checking Grocy for existing product by barcode ...');
  let byb = null;
  try { byb = await fetchJson('GET', `/stock/products/by-barcode/${barcode}`); } catch (e) {
    const msg = String(e || ''); if (msg.includes(' 400 ') || msg.includes(' 404 ')) byb = null; else throw e;
  }
  if (!byb) throw new Error('No product exists for this barcode; cannot remove');
  data('grocy.by_barcode.existing', byb);
  step('Consuming amount 1 via /consume ...');
  const resp = await fetchJson('POST', `/stock/products/by-barcode/${barcode}/consume`, { amount: 1 });
  data('grocy.consume_by_barcode.response', resp);
  return { status: 'ok', message: 'Consumed 1 from existing product by barcode', barcode, operation: 'remove', consumed_amount: 1 };
}

async function run(op, barcode) {
  const logs = [];
  try {
    if (op === 'add') return await processAdd(barcode, logs);
    if (op === 'remove') return await processRemove(barcode, logs);
    throw new Error('Unknown operation');
  } finally {
    // attach logs array to run for the server to collect (optional)
    run.lastLogs = logs;
  }
}

module.exports = { run };


