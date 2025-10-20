# Automation Memory Extension

Manage memories, scheduled tasks, and task flows for Luna.

## Features

- **Memories**: Store and retrieve contextual information as a list of strings
- **Scheduled Tasks**: Run prompts at specified times using cron-like scheduling
- **Task Flows**: Execute sequences of prompts in order

## Configuration

Required environment variables (see `.env`):
- Database credentials (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)

## Tools

All tools follow the naming convention:
- `MEMORY_*` - Memory management
- `SCHEDULE_*` - Scheduled task management  
- `FLOW_*` - Task flow management

## UI

The extension provides a web UI with tabs for:
- Memories
- Scheduled Tasks
- Task Flows

Each UI includes agent selection dropdown for choosing which agent executes the tasks.

