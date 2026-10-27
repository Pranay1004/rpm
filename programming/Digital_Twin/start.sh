#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "/Users/pandeyji/py314env/bin/activate" ]; then
    source /Users/pandeyji/py314env/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

PORT=8080
while lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; do PORT=$((PORT+1)); done
PYTHONPATH=src python3 -m uvicorn webapp.server:app --host 0.0.0.0 --port $PORT --reload

