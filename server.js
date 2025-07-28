const express = require('express');
const cors = require('cors');
const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = 'data/chefbyte.db';
const db = new Database(DB_PATH);

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'dist')));

function getPrimaryKey(table) {
  try {
    const info = db.prepare(`PRAGMA table_info(${table})`).all();
    const pkRow = info.find(c => c.pk === 1);
    return pkRow ? pkRow.name : null;
  } catch (e) {
    return null;
  }
}

app.get('/api/tables', (req, res) => {
  try {
    const rows = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").all();
    res.json(rows.map(r => r.name));
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/tables/:table', (req, res) => {
  const table = req.params.table;
  try {
    const rows = db.prepare(`SELECT * FROM ${table}`).all();
    res.json(rows);
  } catch (e) {
    res.status(400).json({ error: e.message });
  }
});

app.get('/api/tables/:table/info', (req, res) => {
  const table = req.params.table;
  try {
    const info = db.prepare(`PRAGMA table_info(${table})`).all();
    const pkRow = info.find(c => c.pk === 1);
    res.json({ columns: info.map(c => c.name), primaryKey: pkRow ? pkRow.name : null });
  } catch (e) {
    res.status(400).json({ error: e.message });
  }
});

app.put('/api/tables/:table/:id', (req, res) => {
  const table = req.params.table;
  const idVal = req.params.id;
  const data = req.body;
  const pk = getPrimaryKey(table) || 'id';
  const columns = Object.keys(data);
  const set = columns.map(c => `${c} = ?`).join(', ');
  const values = columns.map(c => data[c]);
  values.push(idVal);
  try {
    db.prepare(`UPDATE ${table} SET ${set} WHERE ${pk} = ?`).run(...values);
    res.json({ success: true });
  } catch (e) {
    res.status(400).json({ error: e.message });
  }
});

app.use((req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(3000, () => {
  console.log('Server listening on http://localhost:3000');
});
