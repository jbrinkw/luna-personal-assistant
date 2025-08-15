# CoachByte Technical Overview

CoachByte is a fitness tracking web app built with a Node/Express API, a React front end, and a PostgreSQL database.

## Architecture
- **API**: `extensions/coachbyte/code/node/server.js` exposes REST endpoints for days, sets, weekly splits, personal records, chat, and timers.
- **Database**: `extensions/coachbyte/code/node/db.js` initializes tables such as `daily_logs`, `planned_sets`, `completed_sets`, `split_sets`, `tracked_prs`, `tracked_exercises`, and `timer`.
- **UI**: `extensions/coachbyte/ui` is a Vite-powered React app composed of pages for logs, PRs, and split planning.
- **Agent Tools**: Python scripts in `extensions/coachbyte/code/python` support chat and automation.

## Front-End Flow
### Home Page (`App.jsx`)
- Fetches `/api/days` to list logged workouts with summaries.
- Buttons: **View Details**, **💪 View PRs**, and **📅 Edit Split**.
- Renders `ChatBar.jsx` at the bottom for API-driven chat.

#### Daily Log Page (`DayDetail.jsx`)
- Polls `/api/days/:id` and `/api/timer` for live updates.
- Records completed sets via `/api/days/:id/completed` and displays rest timers.
- Supports editing planned sets (`/api/plan/:id`) and managing completed logs (`/api/completed/:id`).
- Updates workout summaries through `/api/days/:id/summary` and can delete the day with `DELETE /api/days/:id`.

### Back to Home Page
From the home page, other tools are available.

#### Split Planner (`EditSplitPage.jsx`)
- Loads `/api/split` and edits sets by weekday using `/api/split/:day` and `/api/split/plan/:id`.
- Allows relative load percentages, rest times, and ordering.

#### PR Tracker (`PRTracker.jsx`)
- Retrieves personal records from `/api/prs`.
- Manages the tracked exercise list through `/api/tracked-exercises`.

#### Chat Bar (`ChatBar.jsx`)
- Sends user messages to `/api/chat` and displays responses from the Python agent.

## Back-End Notes
- `server.js` boots the Express app, ensures database schema, and serves the React build.
- Additional endpoints include `/api/complete-today-set` for automation, `/api/timer` for rest status, and `/api/chat/memory` to reset chat history.