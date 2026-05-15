#!/bin/bash
if [ "$EUID" -ne 0 ]; then
    if ! pipenv --venv &>/dev/null; then
        echo "Pipenv virtualenv not found, installing dependencies..."
        pipenv install
    fi
    VENV="$(pipenv --venv)"
    exec sudo env VENV="$VENV" PYTHON="$VENV/bin/python3" HOME="$HOME" "$0" "$@"
fi

SESSION="doomscroll"
REPO="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-$(which python3)}"

tmux kill-session -t "$SESSION" 2>/dev/null
tmux new-session -d -s "$SESSION" -x "$(tput cols)" -y "$(tput lines)"
tmux split-window -h -t "$SESSION"

# Left pane (0.0): interceptor
tmux send-keys -t "$SESSION:0.0" \
  "cd $REPO/src/doomscroll-detector/network && source $VENV/bin/activate && $PYTHON deploy.py" Enter

# Right pane (0.1): inference monitor
tmux send-keys -t "$SESSION:0.1" \
  "cd $REPO/src/doomscroll-detector/inference && source $VENV/bin/activate && $PYTHON monitor.py" Enter

tmux attach-session -t "$SESSION"
