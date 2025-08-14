FROM node:20-bookworm-slim

# Install Python and utilities
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-pip python3-venv tini \
  && ln -sf /usr/bin/python3 /usr/local/bin/python \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements first for better layer caching
COPY requirements.txt ./
COPY requirements.txt ./requirements.txt
# Allow pip installs in Debian's externally-managed environment (PEP 668)
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Install Node dependencies for CoachByte (includes dev deps for Vite)
# Install CoachByte API dependencies (new location)
COPY extensions/coachbyte/code/node/package*.json extensions/coachbyte/code/node/
RUN npm --prefix extensions/coachbyte/code/node ci

# Copy the rest of the repo
COPY . .

# Use Python orchestrator instead of shell script

# Expose ports (hub + apps linked from hub)
EXPOSE 8090 8050 5173 3001

ENV CHEF_PORT=8050 \
  COACH_API_PORT=3001 \
  COACH_UI_PORT=5173 \
  HUB_PORT=8090

ENTRYPOINT ["tini", "--"]
CMD ["./start-all.sh"]


