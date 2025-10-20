# Task Flow Execution Tracking

This document describes the real-time task flow execution tracking feature added to the automation_memory extension.

## Features

### 1. Database Schema
- **New Table**: `flow_executions` - tracks the progress of each flow execution
  - `id`: Unique execution ID
  - `flow_id`: Reference to the task_flow being executed
  - `status`: running, completed, or failed
  - `current_prompt_index`: Current prompt being executed (0-based)
  - `total_prompts`: Total number of prompts in the flow
  - `started_at`: Timestamp when execution started
  - `completed_at`: Timestamp when execution finished
  - `error`: Error message if execution failed
  - `prompt_results`: JSONB array of results for each prompt

### 2. Backend Components

#### Flow Runner (`backend/flow_runner.py`)
- Standalone Python script that executes flows
- Runs in the background as a separate process
- Updates execution status in real-time as each prompt completes
- Stores each prompt's response and any errors
- Communicates with Agent API to execute prompts

#### Database Functions (`backend/db.js`)
- `createExecution(flowId, totalPrompts)` - Start tracking a new execution
- `getExecution(id)` - Get execution details by ID
- `listActiveExecutions()` - Get all currently running flows
- `listRecentExecutions(limit)` - Get recent execution history
- `updateExecutionProgress(id, promptIndex, promptResult)` - Update progress
- `completeExecution(id, status, error)` - Mark execution as completed or failed

#### API Endpoints (`backend/server.js`)
- `POST /api/task_flows/:id/run` - Start a flow execution (returns execution_id)
- `GET /api/executions/active` - Get all running executions
- `GET /api/executions/recent?limit=N` - Get recent execution history
- `GET /api/executions/:id` - Get specific execution details

### 3. Frontend Components

#### Active Executions Display
- Shows all currently running flows at the top of the Task Flows tab
- Real-time progress bar showing completion percentage
- Displays current prompt being executed
- Shows the latest agent response
- Auto-refreshes every 2 seconds via polling

#### Execution History
- Toggleable history view showing recent executions
- Color-coded status indicators:
  - 🟢 Green: Completed successfully
  - 🔴 Red: Failed with error
  - 🔵 Blue: Running
- Expandable results showing all prompt/response pairs
- Error messages displayed prominently for failed executions

## Usage

### Running a Flow
1. Navigate to the Task Flows tab
2. Click "Run" on any flow
3. The flow will appear in the "Running Flows" section
4. Watch real-time progress as each prompt executes
5. When complete, it moves to history

### Viewing Results
1. Click "Show History" to see recent executions
2. Expand any execution to see all prompt/response pairs
3. Failed executions show error messages in red

## Technical Details

### Execution Process
1. User clicks "Run" on a flow
2. Backend creates an execution record in the database
3. Backend spawns flow_runner.py as a detached background process
4. Flow runner:
   - Fetches flow details and memories from database
   - Executes each prompt sequentially using the Agent API
   - Updates database after each prompt completes
   - Marks execution as completed or failed when done
5. Frontend polls every 2 seconds and displays live updates

### Data Flow
```
User clicks Run
    ↓
POST /api/task_flows/:id/run
    ↓
Create execution record → Return execution_id
    ↓
Spawn flow_runner.py (background)
    ↓
flow_runner executes prompts
    ↓
Updates database after each prompt
    ↓
Frontend polls /api/executions/active
    ↓
Display real-time progress to user
```

### Error Handling
- Network errors captured and stored in execution record
- Agent API errors displayed to user
- Failed executions marked with status='failed' and error message
- Retryable failures can be run again by clicking Run

## Environment Variables

The flow runner uses these environment variables:
- `AGENT_API_PORT` - Port for Agent API (default: 8080)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Database connection
- `PYTHON_CMD` - Python command to use (default: python3)

## Dependencies

### Python
- `aiohttp` - Async HTTP requests to Agent API
- `psycopg` - Database access

### Node.js
None (uses existing dependencies)





