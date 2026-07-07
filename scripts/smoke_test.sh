#!/usr/bin/env bash
set -euo pipefail

export PORT="${PORT:-3900}"
python3 server.py > /tmp/app-smoke.log 2>&1 &
pid="$!"
trap 'kill "$pid" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  if curl -fs "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

curl -fsS "http://127.0.0.1:$PORT/health"
curl -fsS -X POST "http://127.0.0.1:$PORT/api/items" \
  -H 'content-type: application/json' \
  --data '{"title":"CI smoke item","body":"created by smoke test","status":"open","meta":{"source":"ci"}}' >/tmp/app-smoke-item.json
curl -fsS "http://127.0.0.1:$PORT/api/items" | grep -q "CI smoke item"
