#!/bin/bash
if [ "$EUID" -ne 0 ]; then
    if ! pipenv --venv &>/dev/null; then
        echo "Pipenv virtualenv not found, installing dependencies..."
        pipenv install
    fi
    VENV="$(pipenv --venv)"
    exec sudo env VENV="$VENV" PYTHON="$VENV/bin/python3" "$0" "$@"
fi

SESSION="doomscroll"
REPO="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-$(which python3)}"

tmux kill-session -t "$SESSION" 2>/dev/null
tmux new-session -d -s "$SESSION" -x "$(tput cols)" -y "$(tput lines)"
tmux split-window -h -t "$SESSION"

# Left pane (0): bandwidth monitor
tmux send-keys -t "$SESSION:0.0" \
  "cd $REPO && source $VENV/bin/activate && $PYTHON src/doomscroll-detector/monitor_bandwidth.py" Enter

# Right pane (1): everything else
tmux send-keys -t "$SESSION:0.1" \
  "cd $REPO && source $VENV/bin/activate && $PYTHON src/doomscroll-detector/deploy.py" Enter

tmux attach-session -t "$SESSION"
