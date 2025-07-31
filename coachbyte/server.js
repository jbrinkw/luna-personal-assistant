const express = require('express');
const cors = require('cors');
const path = require('path');
const db = require('./db');

const app = express();
app.use(cors());
app.use(express.json());

// Serve static files from the current directory
app.use(express.static('.'));

// Database is initialized via Python scripts
// db.initDb(false);

app.get('/api/days', async (req, res) => {
  try {
    await db.ensureTodayPlan();
    const days = await db.getAllDays();
    res.json(days);
  } catch (error) {
    console.error('Error getting days:', error);
    res.status(500).json({ error: 'Failed to get days' });
  }
});

app.post('/api/days', async (req, res) => {
  try {
    const { date } = req.body;
    const id = await db.ensureDay(date);
    res.json({ id });
  } catch (error) {
    console.error('Error creating day:', error);
    res.status(500).json({ error: 'Failed to create day' });
  }
});

app.delete('/api/days/:id', async (req, res) => {
  try {
    await db.deleteDay(req.params.id);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting day:', error);
    res.status(500).json({ error: 'Failed to delete day' });
  }
});

app.get('/api/days/:id', async (req, res) => {
  try {
    const data = await db.getDay(req.params.id);
    if (!data) return res.status(404).end();
    res.json(data);
  } catch (error) {
    console.error('Error getting day:', error);
    res.status(500).json({ error: 'Failed to get day' });
  }
});

// Split (weekly plan) endpoints
app.get('/api/split', async (req, res) => {
  try {
    const split = await db.getAllSplit();
    res.json(split);
  } catch (error) {
    console.error('Error getting split:', error);
    res.status(500).json({ error: 'Failed to get split' });
  }
});

app.get('/api/split/:day', async (req, res) => {
  try {
    const items = await db.getSplit(Number(req.params.day));
    res.json(items);
  } catch (error) {
    console.error('Error getting split day:', error);
    res.status(500).json({ error: 'Failed to get split day' });
  }
});

app.post('/api/split/:day', async (req, res) => {
  try {
    const id = await db.addSplit(Number(req.params.day), req.body);
    res.json({ id });
  } catch (error) {
    console.error('Error adding split set:', error);
    res.status(500).json({ error: 'Failed to add split set' });
  }
});

app.put('/api/split/plan/:id', async (req, res) => {
  try {
    await db.updateSplit(Number(req.params.id), req.body);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating split set:', error);
    res.status(500).json({ error: 'Failed to update split set' });
  }
});

app.delete('/api/split/plan/:id', async (req, res) => {
  try {
    await db.deleteSplit(Number(req.params.id));
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting split set:', error);
    res.status(500).json({ error: 'Failed to delete split set' });
  }
});

app.post('/api/days/:id/plan', async (req, res) => {
  try {
    const id = await db.addPlan(req.params.id, req.body);
    res.json({ id });
  } catch (error) {
    console.error('Error adding plan:', error);
    res.status(500).json({ error: 'Failed to add plan' });
  }
});

app.put('/api/plan/:id', async (req, res) => {
  try {
    await db.updatePlan(Number(req.params.id), req.body);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating plan:', error);
    res.status(500).json({ error: 'Failed to update plan' });
  }
});

app.delete('/api/plan/:id', async (req, res) => {
  try {
    await db.deletePlan(Number(req.params.id));
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting plan:', error);
    res.status(500).json({ error: 'Failed to delete plan' });
  }
});

app.post('/api/days/:id/completed', async (req, res) => {
  try {
    // Get the current plan to find the rest time for the next set
    const dayData = await db.getDay(req.params.id);
    const nextSet = dayData.plan.length > 0 ? dayData.plan[0] : null;
    
    const id = await db.addCompleted(req.params.id, req.body);
    
    // If there was a next set, set a timer for its rest period
    if (nextSet && nextSet.rest) {
      try {
        const { spawn } = require('child_process');
        const path = require('path');
        const restSeconds = nextSet.rest; // Use exact seconds
        const timerScript = path.join(__dirname, 'timer_temp.py');
        const pythonProcess = spawn('python', [timerScript, 'set', restSeconds.toString(), 'seconds']);

        pythonProcess.stdout.on('data', (data) => {
          console.log('Timer set:', data.toString().trim());
        });

        pythonProcess.stderr.on('data', (data) => {
          console.error('Timer error:', data.toString().trim());
        });
      } catch (timerError) {
        console.error('Error setting timer:', timerError);
        // Don't fail the main request if timer setting fails
      }
    }
    
    // Return the complete data including timestamp
    const updatedDayData = await db.getDay(req.params.id);
    const completedSet = updatedDayData.completed.find(c => c.id === id);
    
    if (completedSet) {
      res.json({
        id: completedSet.id,
        exercise: completedSet.exercise,
        reps_done: completedSet.reps_done,
        load_done: completedSet.load_done,
        completed_at: completedSet.completed_at
      });
    } else {
      res.json({ id });
    }
  } catch (error) {
    console.error('Error adding completed set:', error);
    res.status(500).json({ error: 'Failed to add completed set' });
  }
});

app.put('/api/completed/:id', async (req, res) => {
  try {
    await db.updateCompleted(Number(req.params.id), req.body);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating completed set:', error);
    res.status(500).json({ error: 'Failed to update completed set' });
  }
});

app.delete('/api/completed/:id', async (req, res) => {
  try {
    await db.deleteCompleted(Number(req.params.id));
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting completed set:', error);
    res.status(500).json({ error: 'Failed to delete completed set' });
  }
});

app.put('/api/days/:id/summary', async (req, res) => {
  try {
    await db.updateSummary(req.params.id, req.body.summary || '');
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating summary:', error);
    res.status(500).json({ error: 'Failed to update summary' });
  }
});

// PR tracking endpoint
app.get('/api/prs', async (req, res) => {
  try {
    const prs = await db.getPRs();
    res.json(prs);
  } catch (error) {
    console.error('Error getting PRs:', error);
    res.status(500).json({ error: 'Failed to get PRs' });
  }
});

// CRUD endpoints for tracked PRs
app.get('/api/tracked-prs', async (req, res) => {
  try {
    const prs = await db.getTrackedPRs();
    res.json(prs);
  } catch (error) {
    console.error('Error getting tracked PRs:', error);
    res.status(500).json({ error: 'Failed to get tracked PRs' });
  }
});

app.put('/api/tracked-prs', async (req, res) => {
  try {
    const { exercise, reps, maxLoad } = req.body;
    await db.upsertTrackedPR(exercise, reps, maxLoad);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error updating tracked PR:', error);
    res.status(500).json({ error: 'Failed to update tracked PR' });
  }
});

app.delete('/api/tracked-prs', async (req, res) => {
  try {
    const { exercise, reps } = req.body;
    await db.deleteTrackedPR(exercise, reps);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting tracked PR:', error);
    res.status(500).json({ error: 'Failed to delete tracked PR' });
  }
});

// CRUD endpoints for tracked exercises (exercise names only)
app.get('/api/tracked-exercises', async (req, res) => {
  try {
    const exercises = await db.getTrackedExercises();
    res.json(exercises);
  } catch (error) {
    console.error('Error getting tracked exercises:', error);
    res.status(500).json({ error: 'Failed to get tracked exercises' });
  }
});

app.post('/api/tracked-exercises', async (req, res) => {
  try {
    const { exercise } = req.body;
    await db.addTrackedExercise(exercise);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error adding tracked exercise:', error);
    res.status(500).json({ error: 'Failed to add tracked exercise' });
  }
});

app.delete('/api/tracked-exercises', async (req, res) => {
  try {
    const { exercise } = req.body;
    await db.removeTrackedExercise(exercise);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error removing tracked exercise:', error);
    res.status(500).json({ error: 'Failed to remove tracked exercise' });
  }
});

// Chat endpoint - connects to Python agent
app.post('/api/chat', async (req, res) => {
  try {
    const { message } = req.body;
    
    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }

    // Create a temporary JSON file with the message data
    const fs = require('fs');
    const path = require('path');
    const crypto = require('crypto');
    
    const tempId = crypto.randomBytes(16).toString('hex');
    const tempFile = path.join(__dirname, `temp_chat_${tempId}.json`);
    
    const chatData = {
      message: message,
      timestamp: new Date().toISOString()
    };
    
    fs.writeFileSync(tempFile, JSON.stringify(chatData));

    // Call Python agent with the temp file
    const { spawn } = require('child_process');
    const pythonProcess = spawn('python', ['chat_agent.py', tempFile]);

    let responseData = '';
    let errorData = '';

    pythonProcess.stdout.on('data', (data) => {
      responseData += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      errorData += data.toString();
    });

    pythonProcess.on('close', (code) => {
      // Clean up temp file if it still exists
      try {
        if (fs.existsSync(tempFile)) {
          fs.unlinkSync(tempFile);
        }
      } catch (cleanupError) {
        console.error('Error cleaning up temp file:', cleanupError);
      }
      
      if (code === 0) {
        res.json({ response: responseData.trim() });
      } else {
        console.error('Python process error:', errorData);
        res.status(500).json({ error: 'Failed to process message' });
      }
    });

  } catch (error) {
    console.error('Error in chat endpoint:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Clear chat memory endpoint
app.delete('/api/chat/memory', async (req, res) => {
  try {
    const { spawn } = require('child_process');
    const pythonProcess = spawn('python', ['-c', `
import sys
sys.path.append('.')
from db import clear_chat_memory

clear_chat_memory()
print("Chat memory cleared")
`]);

    let responseData = '';
    let errorData = '';

    pythonProcess.stdout.on('data', (data) => {
      responseData += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      errorData += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        res.json({ success: true, message: 'Chat memory cleared' });
      } else {
        console.error('Python process error:', errorData);
        res.status(500).json({ error: 'Failed to clear chat memory' });
      }
    });

  } catch (error) {
    console.error('Error clearing chat memory:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get timer status endpoint
app.get('/api/timer', async (req, res) => {
  try {
    const { spawn } = require('child_process');
    const path = require('path');
    const timerScript = path.join(__dirname, 'timer_temp.py');
    const pythonProcess = spawn('python', [timerScript, 'get']);

    let responseData = '';
    let errorData = '';

    pythonProcess.stdout.on('data', (data) => {
      responseData += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      errorData += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const timerStatus = JSON.parse(responseData.trim());
          res.json(timerStatus);
        } catch (parseError) {
          res.status(500).json({ error: 'Failed to parse timer status' });
        }
      } else {
        console.error('Python process error:', errorData);
        res.status(500).json({ error: 'Failed to get timer status' });
      }
    });

  } catch (error) {
    console.error('Error getting timer status:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Complete the next planned set for today (for automation)
app.post('/api/complete-today-set', async (req, res) => {
  try {
    const { spawn } = require('child_process');
    const path = require('path');
    const script = path.join(__dirname, 'complete_next_set.py');
    const pythonProcess = spawn('python', [script]);

    let responseData = '';
    let errorData = '';

    pythonProcess.stdout.on('data', (data) => {
      responseData += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      errorData += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(responseData.trim());
          res.json(result);
        } catch (err) {
          res.json({ message: responseData.trim() });
        }
      } else {
        console.error('Python process error:', errorData);
        res.status(500).json({ error: 'Failed to complete set' });
      }
    });

  } catch (error) {
    console.error('Error completing set:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Serve the React app for the root route
app.get('/', (req, res) => {
  res.sendFile(path.resolve(__dirname, 'index.html'));
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log('Server running on', PORT));
