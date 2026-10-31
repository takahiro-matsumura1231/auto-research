#!/usr/bin/env bash
# Serve a directory over HTTP on 127.0.0.1 so images/figures can be viewed in a browser.
#   bash tools/serve_preview.sh [DIR] [PORT]
# DIR defaults to the repository root; PORT defaults to project.yaml preview.port (8765).
# Runs in a detached tmux session "preview-<port>" if tmux exists, else nohup. Reuses a running server.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
dir="${1:-$root}"
port="${2:-$(grep -A2 '^preview:' "$root/project.yaml" 2>/dev/null | grep -oE 'port:\s*[0-9]+' | grep -oE '[0-9]+' || true)}"
port="${port:-8765}"
dir="$(cd "$dir" && pwd)"
session="preview-$port"

if curl -s -o /dev/null "http://127.0.0.1:$port/" 2>/dev/null; then
  echo "server already running on port $port"
  if command -v tmux >/dev/null && tmux has-session -t "$session" 2>/dev/null; then
    echo "(tmux session $session; restart it if you need a different root: tmux kill-session -t $session)"
  fi
else
  if command -v tmux >/dev/null; then
    tmux new-session -d -s "$session" "cd '$dir' && python3 -m http.server $port --bind 127.0.0.1"
  else
    (cd "$dir" && nohup python3 -m http.server "$port" --bind 127.0.0.1 >/tmp/"$session".log 2>&1 &)
  fi
  sleep 1
  echo "serving $dir on http://localhost:$port/"
fi
echo "over SSH, forward first:  ssh -L $port:localhost:$port <server>"
