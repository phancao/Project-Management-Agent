#!/bin/bash
# Script to tail the backend logs

cd "$(dirname "$0")"

if [ ! -f "logs/backend.log" ]; then
    echo "No log file found. Start the server first with: ./start_backend_with_logs.sh"
    exit 1
fi

echo "Tailing backend logs (Press Ctrl+C to stop)..."
echo "Log file: logs/backend.log"
echo ""
tail -f logs/backend.log

