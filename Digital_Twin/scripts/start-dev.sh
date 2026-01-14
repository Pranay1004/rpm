#!/bin/bash
# Development startup script
# Starts all components in tmux sessions

echo "Starting RPM Digital Twin..."

# Create tmux session
tmux new-session -d -s rpm

# Split and start services
tmux send-keys -t rpm "cd src/backend && npm run dev" Enter
tmux new-window -t rpm -n frontend
tmux send-keys -t rpm:frontend "cd src/frontend && npm run dev" Enter

tmux new-window -t rpm -n analytics
tmux send-keys -t rpm:analytics "cd src/analytics && source venv/bin/activate && python app.py" Enter

tmux new-window -t rpm -n logs
tmux send-keys -t rpm:logs "tail -f logs/combined.log" Enter

echo "Started services in tmux session 'rpm'"
echo ""
echo "Available windows:"
echo "  tmux attach-session -t rpm:backend"
echo "  tmux attach-session -t rpm:frontend"
echo "  tmux attach-session -t rpm:analytics"
echo "  tmux attach-session -t rpm:logs"
echo ""
echo "GUI will open at http://localhost:5173"
echo "API available at http://localhost:3000"
