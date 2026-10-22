#!/usr/bin/env bash
# (Re)start the Ollama server in the background with the settings used for every run.
# There is no systemd in the container, so the server is started by hand.
set -euo pipefail

pkill -x ollama || true   # exact process name, so it cannot match this script itself
sleep 1

# OLLAMA_CONTEXT_LENGTH: same context window for every run.
# OLLAMA_NUM_PARALLEL: 4 requests at once (garak --parallel_attempts 4), only for speed.
OLLAMA_CONTEXT_LENGTH=4096 OLLAMA_NUM_PARALLEL=4 \
    setsid nohup ollama serve > /root/ollama.log 2>&1 < /dev/null &

until curl -sf http://127.0.0.1:11434/api/version > /dev/null; do sleep 1; done
echo "ollama is up: $(curl -s http://127.0.0.1:11434/api/version)"
