#!/usr/bin/env bash
# (Re)start the Ollama server on the laptop with the settings used for the midterm.
# Laptop version of scripts/start_ollama.sh (that one is for the Runpod pod of Assignment 2).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/logs"

pkill -x ollama || true   # exact process name, so it cannot match this script itself
sleep 1

# OLLAMA_HOST: listen on localhost only.
# OLLAMA_CONTEXT_LENGTH: same context window for every request.
# OLLAMA_NUM_PARALLEL=1: one request at a time, so latencies are comparable.
# OLLAMA_MAX_LOADED_MODELS=3: bot (3B) + guard (1B) + judge (7B) stay in memory together;
#   with the default ("auto") Ollama kept only one model loaded and reloaded on every switch.
# OLLAMA_KEEP_ALIVE=30m: do not unload models between requests during a run.
OLLAMA_HOST=127.0.0.1:11434 \
OLLAMA_CONTEXT_LENGTH=4096 \
OLLAMA_NUM_PARALLEL=1 \
OLLAMA_MAX_LOADED_MODELS=3 \
OLLAMA_KEEP_ALIVE=30m \
    nohup ollama serve > "$ROOT/logs/ollama.log" 2>&1 < /dev/null &

# Check the expected answer, not just "something listens on the port".
until curl -sf http://127.0.0.1:11434/api/version | grep -q '"version"'; do sleep 1; done
echo "ollama is up: $(curl -s http://127.0.0.1:11434/api/version)"
