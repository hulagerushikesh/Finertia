#!/usr/bin/env bash
# Start the API for the end-to-end suite: wait for the emulators, seed them,
# then serve. Playwright's webServer runs this and waits on /api/health.
set -euo pipefail

cd "$(dirname "$0")/../../backend"

# The project's venv locally; the job's Python in CI.
PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY=python

export GCLOUD_PROJECT=demo-finertia
export FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
export ALLOWED_ORIGINS=http://127.0.0.1:5175,http://localhost:5175,http://127.0.0.1:5176,http://localhost:5176
# Validation is the slowest call; the suite makes a handful in a minute.
export RATE_LIMIT_VALIDATE_PER_MIN=30

for _ in $(seq 1 60); do
  curl -s -o /dev/null "http://$FIRESTORE_EMULATOR_HOST" && curl -s -o /dev/null "http://$FIREBASE_AUTH_EMULATOR_HOST" && break
  sleep 1
done

# The second API (switched-on features, port 8002) starts after the first has
# seeded the shared emulators, so it skips the seed.
[ -n "${SKIP_SEED:-}" ] || "$PY" scripts/seed_e2e.py
exec "$PY" -m uvicorn main:app --host 127.0.0.1 --port "${API_PORT:-8001}"
