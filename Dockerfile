# Multi-service container for Luna Personal Assistant
# Runs Python FastAPI services and Node-based UIs/APIs via start_all_apps.py

FROM node:20-bullseye AS base

# Install Python 3.11 and build deps
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv python3-dev build-essential git curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Prime layer with Python deps
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy repository
COPY . .

# Install Node deps for Node apps if present (best-effort)
RUN set -eux; \
    for dir in \
      extensions/coachbyte/code/node \
      extensions/coachbyte/ui \
      extensions/automation_memory/backend \
      extensions/automation_memory/ui \
      extensions/grocy/web \
    ; do \
      if [ -f "$dir/package.json" ]; then \
        echo "Installing node deps in $dir"; \
        cd "$dir"; \
        if [ -f package-lock.json ]; then npm ci --silent --no-audit --fund=false; else npm install --silent --no-audit --fund=false; fi; \
        cd - >/dev/null; \
      else \
        echo "Skip $dir (no package.json)"; \
      fi; \
    done

# Expose ports used by services (some may vary at runtime)
EXPOSE 3001 3051 8069 8031 8032 8033 3100

# Default environment
ENV OPENAI_API_PORT=8069 \
    COACH_API_PORT=3001 \
    COACH_UI_PORT=8031 \
    HUB_PORT=8032 \
    AM_UI_PORT=8033 \
    AM_API_PORT=3051 \
    GROCY_IO_WIZ_PORT=3100

# Start all services (logs go to stdout and /app/logs/apps)
CMD ["python3", "core/scripts/start_all_apps.py"]



