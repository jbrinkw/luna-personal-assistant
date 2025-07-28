const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

// Database setup
const dbPath = path.join(__dirname, 'workout.db');
const db = new Database(dbPath);

function generateUuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function loadSampleData() {
  console.log('Loading sample data...');
  
  // Create schema
  db.exec(`
    CREATE TABLE IF NOT EXISTS exercises (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT UNIQUE NOT NULL
    );
    CREATE TABLE IF NOT EXISTS daily_logs (
      id TEXT PRIMARY KEY,
      log_date DATE NOT NULL UNIQUE,
      summary TEXT
    );
    CREATE TABLE IF NOT EXISTS planned_sets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      log_id TEXT REFERENCES daily_logs(id) ON DELETE CASCADE,
      exercise_id INTEGER REFERENCES exercises(id),
      order_num INTEGER NOT NULL,
      reps INTEGER NOT NULL,
      load REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS completed_sets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      log_id TEXT REFERENCES daily_logs(id) ON DELETE CASCADE,
      exercise_id INTEGER REFERENCES exercises(id),
      reps_done INTEGER,
      load_done REAL,
      completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
  `);

  // Clear existing data
  db.exec(`
    DELETE FROM completed_sets;
    DELETE FROM planned_sets;
    DELETE FROM exercises;
    DELETE FROM daily_logs;
  `);

  // Create today's log
  const today = new Date().toISOString().slice(0, 10);
  const logId = generateUuid();
  db.prepare("INSERT INTO daily_logs (id, log_date, summary) VALUES (?, ?, '')").run(logId, today);
  console.log(`Created daily log for ${today}`);

  // Create yesterday's log
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = yesterday.toISOString().slice(0, 10);
  const yesterdayLogId = generateUuid();
  db.prepare("INSERT INTO daily_logs (id, log_date, summary) VALUES (?, ?, ?)").run(yesterdayLogId, yesterdayStr, 'Great workout yesterday! Hit all my targets.');
  console.log(`Created daily log for ${yesterdayStr}`);

  // Add exercises
  const exercises = [
    { name: 'bench press' },
    { name: 'squat' },
    { name: 'deadlift' }
  ];

  const exerciseIds = {};
  exercises.forEach(exercise => {
    const result = db.prepare('INSERT INTO exercises (name) VALUES (?)').run(exercise.name);
    exerciseIds[exercise.name] = result.lastInsertRowid;
    console.log(`Added exercise: ${exercise.name} (ID: ${result.lastInsertRowid})`);
  });

  // Add planned sets
  const plannedSets = [
    { exercise: 'bench press', order_num: 1, reps: 10, load: 45 },
    { exercise: 'bench press', order_num: 2, reps: 8, load: 65 },
    { exercise: 'bench press', order_num: 3, reps: 5, load: 85 },
    { exercise: 'squat', order_num: 4, reps: 10, load: 95 },
    { exercise: 'squat', order_num: 5, reps: 8, load: 135 },
    { exercise: 'squat', order_num: 6, reps: 5, load: 185 },
    { exercise: 'deadlift', order_num: 7, reps: 5, load: 135 },
    { exercise: 'deadlift', order_num: 8, reps: 5, load: 185 },
    { exercise: 'deadlift', order_num: 9, reps: 3, load: 225 }
  ];

  plannedSets.forEach(set => {
    const exerciseId = exerciseIds[set.exercise];
    db.prepare('INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load) VALUES (?, ?, ?, ?, ?)')
      .run(logId, exerciseId, set.order_num, set.reps, set.load);
  });
  console.log(`Added ${plannedSets.length} planned sets for today`);

  // Add planned sets for yesterday
  const yesterdayPlannedSets = [
    { exercise: 'bench press', order_num: 1, reps: 8, load: 50 },
    { exercise: 'bench press', order_num: 2, reps: 6, load: 70 },
    { exercise: 'squat', order_num: 3, reps: 8, load: 100 },
    { exercise: 'squat', order_num: 4, reps: 6, load: 140 },
    { exercise: 'deadlift', order_num: 5, reps: 5, load: 140 },
    { exercise: 'deadlift', order_num: 6, reps: 3, load: 190 }
  ];

  yesterdayPlannedSets.forEach(set => {
    const exerciseId = exerciseIds[set.exercise];
    db.prepare('INSERT INTO planned_sets (log_id, exercise_id, order_num, reps, load) VALUES (?, ?, ?, ?, ?)')
      .run(yesterdayLogId, exerciseId, set.order_num, set.reps, set.load);
  });
  console.log(`Added ${yesterdayPlannedSets.length} planned sets for yesterday`);

  // Add some completed sets
  const completedSets = [
    { exercise: 'bench press', reps_done: 10, load_done: 45 },
    { exercise: 'bench press', reps_done: 8, load_done: 65 },
    { exercise: 'squat', reps_done: 10, load_done: 95 },
    { exercise: 'deadlift', reps_done: 5, load_done: 135 }
  ];

  completedSets.forEach(set => {
    const exerciseId = exerciseIds[set.exercise];
    db.prepare('INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done) VALUES (?, ?, ?, ?)')
      .run(logId, exerciseId, set.reps_done, set.load_done);
  });
  console.log(`Added ${completedSets.length} completed sets for today`);

  // Add completed sets for yesterday (complete workout)
  const yesterdayCompletedSets = [
    { exercise: 'bench press', reps_done: 8, load_done: 50 },
    { exercise: 'bench press', reps_done: 6, load_done: 70 },
    { exercise: 'squat', reps_done: 8, load_done: 100 },
    { exercise: 'squat', reps_done: 6, load_done: 140 },
    { exercise: 'deadlift', reps_done: 5, load_done: 140 },
    { exercise: 'deadlift', reps_done: 3, load_done: 190 }
  ];

  yesterdayCompletedSets.forEach(set => {
    const exerciseId = exerciseIds[set.exercise];
    db.prepare('INSERT INTO completed_sets (log_id, exercise_id, reps_done, load_done) VALUES (?, ?, ?, ?)')
      .run(yesterdayLogId, exerciseId, set.reps_done, set.load_done);
  });
  console.log(`Added ${yesterdayCompletedSets.length} completed sets for yesterday`);

  console.log('Sample data loaded successfully!');
  console.log('Database contains:');
  console.log('- 3 exercises');
  console.log('- 15 planned sets (9 for today, 6 for yesterday)');
  console.log('- 10 completed sets (4 for today, 6 for yesterday)');
  console.log('- 2 daily logs (today and yesterday)');
}

// Run the script
if (require.main === module) {
  try {
    loadSampleData();
  } catch (error) {
    console.error('Error loading sample data:', error);
  } finally {
    db.close();
  }
}

module.exports = { loadSampleData }; 