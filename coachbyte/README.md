# CoachByte Agent Demo

Luna Langflow is a full-stack example of using the OpenAI Agents SDK to manage a workout tracker.  A Python agent talks to a PostgreSQL database using a set of specialized tools.  A small Node/React interface exposes the agent through a web API so you can plan workouts, log sets and track personal records from chat or the UI.

## How the App Works (Conceptual Overview)
- **Chat driven workflow:** user messages are passed to the Python agent which decides which tool to run.
- **Workout database:** all plans and completed sets are stored in PostgreSQL.  The agent can read or modify this data through tools such as `new_daily_plan`, `complete_planned_set` and `update_summary`.
- **Timers and PR tracking:** helper tools manage rest timers and personal-record data.
- **Web interface:** the React app (served by the Node server) visualizes your workout history and provides a chat bar that talks to the agent.

### What You Can Do
- Create or edit today’s workout plan and a weekly split.
- Mark sets as completed and automatically start rest timers.
- Save daily summaries and query recent history.
- Track personal records and ask the agent about them.

## Developer Guide
The project combines a Python backend with a small JavaScript frontend.

### Folder Structure
- `agent.py` and `tools.py` – OpenAI agent setup and tool implementations.
- `db.py` – PostgreSQL helpers and schema creation.
- `server.js` – Express server acting as an API gateway and invoking the Python agent.
- `src/` – React components served via Vite.

### Setup
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Configure environment variables for PostgreSQL (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) and your `OPENAI_API_KEY`.  See `db_config.py` for details.
4. (Optional) load sample data:
   ```bash
   python load_sample_data.py
   ```

### Running
- Development mode with hot reload for the UI and API:
  ```bash
  npm run dev-all
  ```
- Production style server:
  ```bash
  npm start
  ```
Then open the web interface at `http://localhost:3001`.

For database migration steps or more details on PostgreSQL configuration see `README_POSTGRES.md`.

### Home Assistant Integration
The server exposes a helper endpoint to complete the next planned set for today.

- **POST `/api/complete-today-set`** – runs the `complete_planned_set` helper and
  returns a JSON message.

To trigger this from a Zigbee button you can create a `rest_command` in
`configuration.yaml`:

```yaml
rest_command:
  complete_workout_set:
    url: "http://<server-ip>:3001/api/complete-today-set"
    method: POST
```

Create an automation for your button that calls `rest_command.complete_workout_set`
whenever it is pressed. Each press logs the next set and starts the rest timer
just like clicking **Complete Set** in the web UI.
