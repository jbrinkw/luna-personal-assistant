require('dotenv').config();
const { Pool } = require('pg');
const { format } = require('date-fns');

function getTodayInEst() {
  const estFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
  const parts = estFormatter.formatToParts(new Date());
  const partValue = (type) => parts.find(p => p.type === type).value;
  return `${partValue('year')}-${partValue('month')}-${partValue('day')}`;
}

// Database configuration
const dbConfig = {
  host: process.env.DB_HOST || '192.168.0.239',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'workout_tracker',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || '',
};

const pool = new Pool(dbConfig);

async function initDb(sample = false) {
  const client = await pool.connect();
  try {
    await client.query(`
      CREATE TABLE IF NOT EXISTS exercises (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE NOT NULL
      );
      CREATE TABLE IF NOT EXISTS daily_logs (
        id VARCHAR(255) PRIMARY KEY,
        log_date DATE NOT NULL UNIQUE,
        summary TEXT
      );
      CREATE TABLE IF NOT EXISTS planned_sets (
        id SERIAL PRIMARY KEY,
        log_id VARCHAR(255) REFERENCES daily_logs(id) ON DELETE CASCADE,
        exercise_id INTEGER REFERENCES exercises(id),
        order_num INTEGER NOT NULL,
        reps INTEGER NOT NULL,
        load REAL NOT NULL,
        rest INTEGER DEFAULT 60,
        relative BOOLEAN DEFAULT FALSE
      );
      CREATE TABLE IF NOT EXISTS completed_sets (
        id SERIAL PRIMARY KEY,
        log_id VARCHAR(255) REFERENCES daily_logs(id) ON DELETE CASCADE,
        exercise_id INTEGER REFERENCES exercises(id),
        planned_set_id INTEGER REFERENCES planned_sets(id),
        reps_done INTEGER,
        load_done REAL,
        completed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
      );
      CREATE TABLE IF NOT EXISTS tracked_prs (
        exercise VARCHAR(255) NOT NULL,
        reps INTEGER NOT NULL,
        max_load REAL NOT NULL,
        PRIMARY KEY (exercise, reps)
      );
      CREATE TABLE IF NOT EXISTS tracked_exercises (
        exercise VARCHAR(255) PRIMARY KEY
      );
      CREATE TABLE IF NOT EXISTS split_sets (
        id SERIAL PRIMARY KEY,
        day_of_week INTEGER NOT NULL,
        exercise_id INTEGER REFERENCES exercises(id),
        order_num INTEGER NOT NULL,
        reps INTEGER NOT NULL,
        load REAL NOT NULL,
        rest INTEGER DEFAULT 60,
        relative BOOLEAN DEFAULT FALSE
      );
    `);
    
    // Add 'relative' column to split_sets if it doesn't exist, for backward compatibility
    await client.query(`
      DO $$
      BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='split_sets' AND column_name='relative') THEN
          ALTER TABLE split_sets ADD COLUMN relative BOOLEAN DEFAULT FALSE;
        END IF;
      END $$;
    `);

    // Add 'relative' column to planned_sets if it doesn't exist, for backward compatibility
    await client.query(`
      DO $$
      BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='planned_sets' AND column_name='relative') THEN
          ALTER TABLE planned_sets ADD COLUMN relative BOOLEAN DEFAULT FALSE;
        END IF;
      END $$;
    `);

    // Update completed_at column to use TIMESTAMPTZ for proper timezone handling
    await client.query(`
      DO $$
      BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='completed_sets' AND column_name='completed_at' AND data_type='timestamp without time zone') THEN
          ALTER TABLE completed_sets ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC';
        END IF;
      END $$;
    `);

    // Initialize with default tracked exercises if none exist
    const result = await client.query('SELECT COUNT(*) FROM tracked_exercises');
    if (parseInt(result.rows[0].count) === 0) {
      await client.query(`
        INSERT INTO tracked_exercises (exercise) VALUES 
        ('Bench Press'), ('Squat'), ('Deadlift')
      `);
    }
    
    if (sample) {
      const exercisesExist = await client.query('SELECT COUNT(*) FROM exercises');
      if (parseInt(exercisesExist.rows[0].count) === 0) {
        await populateSample(client);
      }
    }
  } finally {
    client.release();
  }
}

async function getExerciseId(name) {
  const client = await pool.connect();
  try {
    // First, try to find an exercise with case-insensitive matching.
    let result = await client.query('SELECT id FROM exercises WHERE LOWER(name) = LOWER($1)', [name]);
    
    // If an exercise is found, return its ID.
    if (result.rows.length > 0) {
      return result.rows[0].id;
    }
    
    // If no exercise is found, create a new one with the provided name.
    result = await client.query('INSERT INTO exercises (name) VALUES ($1) RETURNING id', [name]);
    return result.rows[0].id;
  } finally {
    client.release();
  }
}

async function ensureDay(dateStr) {
  const client = await pool.connect();
  try {
    const result = await client.query('SELECT id FROM daily_logs WHERE log_date = $1', [dateStr]);
    if (result.rows.length > 0) {
      return result.rows[0].id;
    }
    const logId = generateUuid();
    await client.query('INSERT INTO daily_logs (id, log_date, summary) VALUES ($1, $2, $3)', [logId, dateStr, '']);
    return logId;
  } finally {
    client.release();
  }
}

async function ensureTodayPlan() {
  const today = getTodayInEst();
  const logId = await ensureDay(today);
  await applySplitIfEmpty(logId, today);
  return logId;
}

function generateUuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

async function getAllDays() {
  const client = await pool.connect();
  try {
    const result = await client.query('SELECT id, log_date, summary FROM daily_logs ORDER BY log_date DESC');
    return result.rows;
  } finally {
    client.release();
  }
}

async function deleteDay(id) {
  const client = await pool.connect();
  try {
    await client.query('DELETE FROM daily_logs WHERE id = $1', [id]);
  } finally {
    client.release();
  }
}

async function getSplit(dayOfWeek) {
  const client = await pool.connect();
  try {
    const result = await client.query(
      `SELECT ss.id, e.name as exercise, ss.reps, ss.load, ss.rest, ss.order_num, ss.relative
       FROM split_sets ss JOIN exercises e ON ss.exercise_id = e.id
       WHERE ss.day_of_week = $1 ORDER BY ss.order_num`,
      [dayOfWeek]
    );
    return result.rows;
  } finally {
    client.release();
  }
}

async function getAllSplit() {
  const client = await pool.connect();
  try {
    const result = await client.query(
      `SELECT ss.id, ss.day_of_week, e.name as exercise, ss.reps, ss.load, ss.rest, ss.order_num, ss.relative
       FROM split_sets ss JOIN exercises e ON ss.exercise_id = e.id
       ORDER BY ss.day_of_week, ss.order_num`
    );
    return result.rows;
  } finally {
    client.release();
  }
}

async function addSplit(dayOfWeek, item) {
  const client = await pool.connect();
  try {
    const exId = await getExerciseId(item.exercise);
    const rest = item.rest || 60;
    const result = await client.query(
      'INSERT INTO split_sets (day_of_week, exercise_id, order_num, reps, load, rest, relative) VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id',
      [dayOfWeek, exId, item.order_num, item.reps, item.load, rest, item.relative || false]
    );
    return result.rows[0].id;
  } finally {
    client.release();
  }
}

async function updateSplit(id, item) {
  const client = await pool.connect();
  try {
    const exId = await getExerciseId(item.exercise);
    const rest = item.rest || 60;
    await client.query(
      'UPDATE split_sets SET exercise_id=$1, order_num=$2, reps=$3, load=$4, rest=$5, relative=$6 WHERE id=$7',
      [exId, item.order_num, item.reps, item.load, rest, item.relative || false, id]
    );
  } finally {
    client.release();
  }
}

async function deleteSplit(id) {
  const client = await pool.connect();
  try {
    await client.query('DELETE FROM split_sets WHERE id = $1', [id]);
  } finally {
    client.release();
  }
}

async function applySplitIfEmpty(logId, logDate) {
  const client = await pool.connect();
  try {
    const countRes = await client.query('SELECT COUNT(*) FROM planned_sets WHERE log_id = $1', [logId]);
    if (parseInt(countRes.rows[0].count) > 0) return;
    // By appending T00:00:00, we ensure this is parsed as a local date, not UTC
    const dow = new Date(logDate + 'T00:00:00').getDay();
    const splitRes = await client.query(
      `SELECT ss.exercise_id, e.name as exercise, ss.order_num, ss.reps, ss.load, ss.rest, ss.relative
       FROM split_sets ss JOIN exercises e ON ss.exercise_id = e.id
       WHERE ss.day_of_week = $1 ORDER BY ss.order_num`, [dow]);

    const prs = await getPRs();
    const oneRMs = {};
    for (const [ex, records] of Object.entries(prs)) {
      let max = 0;
      for (const r of records) {
        const est = r.reps === 1 ? r.maxLoad : r.maxLoad * (1 + r.reps / 30);
        if (est > max) max = est;
      }
      oneRMs[ex] = max;
    }

    for (const row of splitRes.rows) {
      let load = row.load;
      // For relative weights, store the original percentage value
      // The actual weight will be calculated dynamically in the UI
      await client.query('INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load, rest, relative) VALUES ($1,$2,$3,$4,$5,$6,$7)',
        [logId, row.exercise_id, row.order_num, row.reps, load, row.rest, row.relative || false]);
    }
  } finally {
    client.release();
  }
}

async function getDay(id) {
  const client = await pool.connect();
  try {
    const logResult = await client.query('SELECT id, log_date, summary FROM daily_logs WHERE id = $1', [id]);
    if (logResult.rows.length === 0) return null;

    const log = logResult.rows[0];

    // If there is no plan for this day, load from weekly split
    // Re-format the date to a string to ensure consistent processing
    const dateString = format(log.log_date, 'yyyy-MM-dd');
    await applySplitIfEmpty(id, dateString);

    const planResult = await client.query(`
    SELECT ps.id, e.name as exercise, ps.reps, ps.load, ps.rest, ps.order_num, ps.relative
    FROM planned_sets ps 
    JOIN exercises e ON ps.exercise_id = e.id
    LEFT JOIN completed_sets cs ON ps.id = cs.planned_set_id
    WHERE ps.log_id = $1 AND cs.id IS NULL
    ORDER BY ps.order_num
  `, [id]);
    
    // Calculate actual weights for relative loads
    const prs = await getPRs();
    const oneRMs = {};
    for (const [ex, records] of Object.entries(prs)) {
      let max = 0;
      for (const r of records) {
        const est = r.reps === 1 ? r.maxLoad : r.maxLoad * (1 + r.reps / 30);
        if (est > max) max = est;
      }
      oneRMs[ex] = max;
    }

    // Update plan with calculated weights for relative loads
    const planWithCalculatedWeights = planResult.rows.map(row => {
      if (row.relative) {
        const rm = oneRMs[row.exercise.toLowerCase()];
        const calculatedLoad = rm ? Math.round(rm * row.load / 100) : 0;
        return {
          ...row,
          calculatedLoad, // Store the calculated weight
          originalLoad: row.load // Store the original percentage
        };
      }
      return {
        ...row,
        calculatedLoad: row.load, // For absolute weights, calculated = original
        originalLoad: row.load
      };
    });
    
    const completedResult = await client.query(`
      SELECT cs.id, e.name as exercise, cs.planned_set_id, cs.reps_done, cs.load_done, cs.completed_at
      FROM completed_sets cs JOIN exercises e ON cs.exercise_id = e.id
      WHERE cs.log_id = $1
      ORDER BY cs.completed_at DESC NULLS LAST
    `, [id]);
    
    return {
      log,
      plan: planWithCalculatedWeights,
      completed: completedResult.rows
    };
  } finally {
    client.release();
  }
}

async function addPlan(logId, item) {
  const client = await pool.connect();
  try {
    const exId = await getExerciseId(item.exercise);
    const rest = item.rest || 60; // Default to 60 seconds if not provided
    const result = await client.query(
      'INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load, rest, relative) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id',
      [logId, exId, item.order_num, item.reps, item.load, rest, item.relative || false]
    );
    return result.rows[0].id;
  } finally {
    client.release();
  }
}

async function updatePlan(id, item) {
  const client = await pool.connect();
  try {
    const exId = await getExerciseId(item.exercise);
    const rest = item.rest || 60; // Default to 60 seconds if not provided
    await client.query(
      'UPDATE planned_sets SET exercise_id = $1, order_num = $2, reps = $3, load = $4, rest = $5, relative = $6 WHERE id = $7',
      [exId, item.order_num, item.reps, item.load, rest, item.relative || false, id]
    );
  } finally {
    client.release();
  }
}

async function deletePlan(id) {
  const client = await pool.connect();
  try {
    await client.query('DELETE FROM planned_sets WHERE id = $1', [id]);
  } finally {
    client.release();
  }
}

async function addCompleted(logId, item) {
  const client = await pool.connect();
  try {
    const exId = await getExerciseId(item.exercise);
    const result = await client.query(
      'INSERT INTO completed_sets (log_id, exercise_id, planned_set_id, reps_done, load_done, completed_at) VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP) RETURNING id',
      [logId, exId, item.planned_set_id || null, item.reps_done, item.load_done]
    );
    return result.rows[0].id;
  } finally {
    client.release();
  }
}

async function updateCompleted(id, item) {
  const client = await pool.connect();
  try {
    const exId = await getExerciseId(item.exercise);
    await client.query(
      'UPDATE completed_sets SET exercise_id = $1, planned_set_id = $2, reps_done = $3, load_done = $4 WHERE id = $5',
      [exId, item.planned_set_id || null, item.reps_done, item.load_done, id]
    );
  } finally {
    client.release();
  }
}

async function deleteCompleted(id) {
  const client = await pool.connect();
  try {
    await client.query('DELETE FROM completed_sets WHERE id = $1', [id]);
  } finally {
    client.release();
  }
}

async function updateSummary(id, summary) {
  const client = await pool.connect();
  try {
    await client.query('UPDATE daily_logs SET summary = $1 WHERE id = $2', [summary, id]);
  } finally {
    client.release();
  }
}

async function getPRs() {
  const client = await pool.connect();
  try {
    // Get tracked exercises from database instead of hardcoded list
    const trackedResult = await client.query('SELECT exercise FROM tracked_exercises');
    const trackedExercises = trackedResult.rows.map(row => row.exercise.toLowerCase());
    
    if (trackedExercises.length === 0) {
      return {}; // No exercises being tracked
    }
    
    const result = await client.query(`
      SELECT 
        LOWER(e.name) as exercise,
        cs.reps_done,
        MAX(cs.load_done) as "maxLoad"
      FROM completed_sets cs
      JOIN exercises e ON cs.exercise_id = e.id
      WHERE LOWER(e.name) = ANY($1)
        AND cs.reps_done > 0
        AND cs.load_done > 0
      GROUP BY LOWER(e.name), cs.reps_done
      ORDER BY LOWER(e.name), cs.reps_done
    `, [trackedExercises]);
    
    // Group by exercise
    const prsByExercise = {};
    for (const row of result.rows) {
      if (!prsByExercise[row.exercise]) {
        prsByExercise[row.exercise] = [];
      }
      prsByExercise[row.exercise].push({
        reps: row.reps_done,
        maxLoad: row.maxLoad
      });
    }
    
    return prsByExercise;
  } finally {
    client.release();
  }
}

async function getTrackedPRs() {
  const client = await pool.connect();
  try {
    const result = await client.query(
      'SELECT exercise, reps, max_load FROM tracked_prs ORDER BY exercise, reps'
    );
    const prsByExercise = {};
    for (const row of result.rows) {
      if (!prsByExercise[row.exercise]) {
        prsByExercise[row.exercise] = [];
      }
      prsByExercise[row.exercise].push({
        reps: row.reps,
        maxLoad: row.max_load,
      });
    }
    return prsByExercise;
  } finally {
    client.release();
  }
}

async function upsertTrackedPR(exercise, reps, maxLoad) {
  const client = await pool.connect();
  try {
    await client.query(
      `INSERT INTO tracked_prs (exercise, reps, max_load)
       VALUES ($1, $2, $3)
       ON CONFLICT (exercise, reps)
       DO UPDATE SET max_load = EXCLUDED.max_load`,
      [exercise, reps, maxLoad]
    );
  } finally {
    client.release();
  }
}

async function deleteTrackedPR(exercise, reps) {
  const client = await pool.connect();
  try {
    await client.query(
      'DELETE FROM tracked_prs WHERE exercise = $1 AND reps = $2',
      [exercise, reps]
    );
  } finally {
    client.release();
  }
}

async function getTrackedExercises() {
  const client = await pool.connect();
  try {
    const result = await client.query('SELECT exercise FROM tracked_exercises ORDER BY exercise');
    return result.rows.map(row => row.exercise);
  } finally {
    client.release();
  }
}

async function addTrackedExercise(exercise) {
  const client = await pool.connect();
  try {
    await client.query(
      'INSERT INTO tracked_exercises (exercise) VALUES ($1) ON CONFLICT (exercise) DO NOTHING',
      [exercise]
    );
  } finally {
    client.release();
  }
}

async function removeTrackedExercise(exercise) {
  const client = await pool.connect();
  try {
    await client.query('DELETE FROM tracked_exercises WHERE exercise = $1', [exercise]);
  } finally {
    client.release();
  }
}

async function populateSample(client) {
  // Clear existing data for a clean slate
  await client.query('DELETE FROM completed_sets');
  await client.query('DELETE FROM planned_sets');
  await client.query('DELETE FROM split_sets');
  await client.query('DELETE FROM daily_logs');
  await client.query('DELETE FROM exercises');

  // Define exercises
  const exercises = [
    'Bench Press', 'Squat', 'Deadlift', 'Overhead Press',
    'Pull-up', 'Bent Over Row', 'Leg Press', 'Bicep Curl', 'Tricep Extension',
    'Plank', 'Running'
  ];
  const exIds = {};
  for (const name of exercises) {
    exIds[name] = await getExerciseId(name);
  }

  // Define a 7-day split
  const sampleSplit = [
    { day: 0, name: 'Active Recovery', workouts: [ // Sunday
      { ex: 'Running', sets: [{ reps: 1, load: 20, rest: 0, order: 1 }] }, // 20 minutes
      { ex: 'Plank', sets: [{ reps: 1, load: 60, rest: 60, order: 2 }] } // 60 seconds
    ]},
    { day: 1, name: 'Push Day', workouts: [ // Monday
      { ex: 'Bench Press', sets: [{ reps: 5, load: 135, rest: 90, order: 1 }, { reps: 5, load: 135, rest: 90, order: 2 }] },
      { ex: 'Overhead Press', sets: [{ reps: 8, load: 80, rest: 75, order: 3 }] },
      { ex: 'Tricep Extension', sets: [{ reps: 10, load: 40, rest: 60, order: 4 }] }
    ]},
    { day: 2, name: 'Core & Cardio', workouts: [ // Tuesday
      { ex: 'Plank', sets: [{ reps: 3, load: 60, rest: 60, order: 1 }] }, // 3 sets of 60s
      { ex: 'Running', sets: [{ reps: 1, load: 15, rest: 0, order: 2 }] } // 15 minutes
    ]},
    { day: 3, name: 'Pull Day', workouts: [ // Wednesday
      { ex: 'Deadlift', sets: [{ reps: 3, load: 225, rest: 120, order: 1 }] },
      { ex: 'Pull-up', sets: [{ reps: 8, load: 0, rest: 75, order: 2 }] },
      { ex: 'Bent Over Row', sets: [{ reps: 8, load: 115, rest: 75, order: 3 }] },
      { ex: 'Bicep Curl', sets: [{ reps: 10, load: 30, rest: 60, order: 4 }] }
    ]},
    { day: 4, name: 'Active Recovery', workouts: [ // Thursday
      { ex: 'Running', sets: [{ reps: 1, load: 25, rest: 0, order: 1 }] } // 25 minutes
    ]},
    { day: 5, name: 'Leg Day', workouts: [ // Friday
      { ex: 'Squat', sets: [{ reps: 5, load: 185, rest: 120, order: 1 }] },
      { ex: 'Leg Press', sets: [{ reps: 10, load: 250, rest: 90, order: 2 }] }
    ]},
    { day: 6, name: 'Conditioning', workouts: [ // Saturday
      { ex: 'Plank', sets: [{ reps: 3, load: 75, rest: 60, order: 1 }] },
      { ex: 'Running', sets: [{ reps: 1, load: 10, rest: 0, order: 2 }] } // 10 min high intensity
    ]},
  ];

  for (const daySplit of sampleSplit) {
    for (const workout of daySplit.workouts) {
      for (const set of workout.sets) {
        await client.query(
          `INSERT INTO split_sets (day_of_week, exercise_id, order_num, reps, load, rest)
           VALUES ($1, $2, $3, $4, $5, $6)`,
          [daySplit.day, exIds[workout.ex], set.order, set.reps, set.load, set.rest]
        );
      }
    }
  }

  // Create logs for the past 2 days
  const todayStr = getTodayInEst();
  const today = new Date(`${todayStr}T00:00:00`); // Ensure parsing is consistent
  const dates = [new Date(today), new Date(today)];
  dates[0].setDate(today.getDate() - 2);
  dates[1].setDate(today.getDate() - 1);
  const dateStrings = dates.map(d => format(d, 'yyyy-MM-dd'));

  for (const dateStr of dateStrings) {
    const logId = await ensureDay(dateStr);
    const dow = new Date(dateStr).getDay();
    const daySplit = sampleSplit.find(s => s.day === dow);
    if (daySplit) {
      // Add planned sets
      for (const workout of daySplit.workouts) {
        for (const set of workout.sets) {
          const planRes = await client.query(
            `INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load, rest)
             VALUES ($1, $2, $3, $4, $5, $6) RETURNING id`,
            [logId, exIds[workout.ex], set.order, set.reps, set.load, set.rest]
          );
          // Add a completed set for some of the planned sets
          if (Math.random() > 0.3) { // ~70% chance to complete a set
            await client.query(
              `INSERT INTO completed_sets (log_id, exercise_id, planned_set_id, reps_done, load_done)
               VALUES ($1, $2, $3, $4, $5)`,
              [logId, exIds[workout.ex], planRes.rows[0].id, set.reps - Math.floor(Math.random() * 2), set.load]
            );
          }
        }
      }
    }
  }
}

module.exports = {
  initDb,
  ensureDay,
  ensureTodayPlan,
  getAllDays,
  getDay,
  addPlan,
  updatePlan,
  deletePlan,
  addCompleted,
  updateCompleted,
  deleteCompleted,
  updateSummary,
  deleteDay,
  getSplit,
  getAllSplit,
  addSplit,
  updateSplit,
  deleteSplit,
  getPRs,
  getTrackedPRs,
  upsertTrackedPR,
  deleteTrackedPR,
  getTrackedExercises,
  addTrackedExercise,
  removeTrackedExercise,
};
