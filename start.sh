#!/bin/bash
# Chart Digitizer — start the web app
# Usage: ./start.sh [port]

set -e

PORT=${1:-5001}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Activate virtual environment if present (inside the project, or one level up)
for VENV in "$SCRIPT_DIR/venv/bin/activate" "$SCRIPT_DIR/../venv/bin/activate"; do
  if [ -f "$VENV" ]; then
    source "$VENV"
    break
  fi
done

echo "Starting Chart Digitizer on http://localhost:$PORT"
echo "Open your browser at: http://localhost:$PORT"
PORT=$PORT python3 "$SCRIPT_DIR/app.py"
