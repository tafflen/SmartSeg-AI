#!/usr/bin/env bash
# Starts the local SmartSeg stack; Ctrl+C stops every child process.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
if [[ ! -f "$VENV/bin/python" ]]; then echo "Missing .venv. Follow README Quick Start first."; exit 1; fi
cleanup() { trap - INT TERM EXIT; kill "${AI_PID:-}" "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true; wait 2>/dev/null || true; }
trap cleanup INT TERM EXIT
prefix() { sed -u "s/^/[$1] /"; }
(
  cd "$ROOT/ai-engine"; "$VENV/bin/python" main.py 2>&1 | prefix AI
) & AI_PID=$!
(
  cd "$ROOT/backend"; "$VENV/bin/python" -m uvicorn main:app --reload 2>&1 | prefix BACKEND
) & BACKEND_PID=$!
(
  cd "$ROOT/frontend"; npm run dev 2>&1 | prefix FRONTEND
) & FRONTEND_PID=$!
echo "SmartSeg started. Dashboard: http://localhost:5173  API: http://localhost:8000"
wait
