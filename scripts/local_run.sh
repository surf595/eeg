#!/usr/bin/env bash
set -euo pipefail

echo "[1/6] Starting Postgres + Redis"
docker compose up -d postgres redis

echo "[2/6] Installing backend deps"
pip install -r requirements.txt

echo "[3/6] Starting backend (http://127.0.0.1:8000)"
uvicorn backend.main:app --reload &
BACK_PID=$!

sleep 2

echo "[4/6] Running reindex"
python -m backend.app.index_eeg_library

echo "[5/6] Starting frontend"
(
  cd frontend
  npm install
  npm run dev
) &
FRONT_PID=$!

echo "[6/6] Open catalog: http://127.0.0.1:3000/catalog"
echo "Press Ctrl+C to stop"
trap 'kill $BACK_PID $FRONT_PID' INT TERM
wait
