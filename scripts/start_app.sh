#!/usr/bin/env bash
# Start the app in the background on 127.0.0.1:8000 and wait until /health answers
# with the expected system prompt hash (not just "something listens on the port").
# Usage: bash scripts/start_app.sh      Stop: pkill -f "uvicorn app.main:create_app"
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p logs

expected=$(.venv/bin/python -c "from app.settings import load_settings; print(load_settings().system_prompt_sha256)")
pkill -f "uvicorn app.main:create_app" || true
sleep 1
nohup .venv/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 \
    > logs/uvicorn.log 2>&1 < /dev/null &

for _ in $(seq 1 60); do
    if curl -sf http://127.0.0.1:8000/health | grep -q "$expected"; then
        echo "app is up: $(curl -s http://127.0.0.1:8000/health)"
        exit 0
    fi
    sleep 1
done
echo "app did not start, see logs/uvicorn.log"
exit 1
