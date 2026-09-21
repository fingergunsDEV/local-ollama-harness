#!/usr/bin/env bash
# Start the strictly loopback-local backend and frontend in separate terminals.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "backend" ]]; then
  cd "$ROOT/backend"
  exec uvicorn app.main:app --host 127.0.0.1 --port 8000
elif [[ "${1:-}" == "frontend" ]]; then
  cd "$ROOT/frontend"
  exec npm run dev
else
  cat <<'USAGE'
Usage:
  ./run-local.sh backend    # terminal 1: FastAPI on 127.0.0.1:8000
  ./run-local.sh frontend   # terminal 2: Next.js on localhost:3000

Copy backend/.env.example to backend/.env and set a dedicated WORKSPACE_ROOT first.
USAGE
fi
