#!/bin/bash
# Start automation_memory UI on specified port
PORT=${1:-5200}
export PORT=$PORT
npm run dev

