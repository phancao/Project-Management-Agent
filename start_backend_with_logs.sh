#!/bin/bash
# Script to start the backend server with logs visible

cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Starting backend server with debug logging..."
echo "Logs will be written to: logs/backend.log"
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server with output redirected to log file and also to terminal
uv run server.py --host localhost --port 8000 --log-level debug 2>&1 | tee logs/backend.log

