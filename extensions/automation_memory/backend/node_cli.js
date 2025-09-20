#!/usr/bin/env node
const db = require('./db/index');

const [,, cmd, ...args] = process.argv;
db.init();

async function main() {
  try {
    if (cmd === 'get_flow') {
      const callName = (args[0] || '').toString();
      const { getFlowByName } = db;
      const row = getFlowByName(callName);
      if (!row) return console.log('{}');
      return console.log(JSON.stringify({ id: row.id, call_name: row.call_name, prompts: row.prompts }));
    }
    console.log('{}');
  } catch (e) {
    console.error(String(e));
    process.exit(1);
  }
}

main();





