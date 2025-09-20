const db = require('../db/index');
const { spawn } = require('child_process');
const path = require('path');

function estNowHHMMAndDOW() {
  const fmt = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false, weekday: 'short' });
  const parts = fmt.formatToParts(new Date());
  const obj = Object.fromEntries(parts.map(p => [p.type, p.value]));
  const hhmm = `${obj.hour}:${obj.minute}`;
  const dowIndex = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].indexOf(obj.weekday);
  return { hhmm, dowIndex };
}

async function tick() {
  try {
    const { hhmm, dowIndex } = estNowHHMMAndDOW();
    const all = await db.listSchedules();
    for (const s of (all || [])) {
      if (!s.enabled) continue;
      if (s.time_of_day !== hhmm) continue;
      const days = Array.isArray(s.days_of_week) && s.days_of_week.length === 7 ? s.days_of_week : [false,false,false,false,false,false,false];
      if (!days[dowIndex]) continue;
      // Fire via Python runner using active agent path
      const nowEst = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date());
      console.log(`[scheduler fired] ${nowEst} — ${s.prompt}`);
      const repoRoot = path.resolve(__dirname, '../../../..');
      const runner = path.join(repoRoot, 'extensions', 'automation_memory', 'backend', 'services', 'flow_runner', 'run_prompt.py');
      const py = spawn('python', [runner, s.prompt], { stdio: 'inherit', cwd: repoRoot });
      py.on('error', (e) => console.error('[scheduler] spawn error', e));
    }
  } catch (e) {
    console.error('[scheduler] tick error', e);
  }
}

function start() {
  // Start minute interval; first tick will occur on next minute boundary
  setInterval(() => { tick().catch((e)=>console.error('[scheduler] tick error', e)); }, 60 * 1000);
  console.log('[scheduler] started (EST minute tick)');
}

module.exports = { start };





