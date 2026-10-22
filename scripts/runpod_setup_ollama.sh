#!/usr/bin/env bash
# Runs ON a fresh Runpod pod (image runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404).
# Installs Ollama, starts it on 127.0.0.1 only (we reach it through an SSH tunnel,
# never through a public proxy URL: Ollama has no authentication), pulls the given
# models, and starts a watchdog that deletes the pod after MAX_MINUTES so a
# forgotten pod cannot keep billing.
#
# Usage (from the laptop):
#   ssh <pod> 'MAX_MINUTES=75 bash -s llama-guard3:1b llama3.1:8b' < scripts/runpod_setup_ollama.sh
set -euo pipefail

MAX_MINUTES=${MAX_MINUTES:?set MAX_MINUTES, e.g. 75}
OLLAMA_VERSION=0.40.8   # same version as on the laptop

echo "== 1. watchdog: this pod deletes itself after $MAX_MINUTES minutes"
# The pod's own id and a pod-scoped API key are in PID 1's environment (set by Runpod).
cat > /root/watchdog.sh <<EOF
#!/bin/bash
eval "\$(tr "\\0" "\\n" < /proc/1/environ | grep -E "^RUNPOD_(POD_ID|API_KEY)=" | sed "s/^/export /")"
sleep $((MAX_MINUTES * 60))
date -u
# Old (v1) and new runpodctl syntax, then the REST API as the last resort.
runpodctl remove pod "\$RUNPOD_POD_ID" || runpodctl pod remove "\$RUNPOD_POD_ID" || \
    curl -s -X DELETE "https://rest.runpod.io/v1/pods/\$RUNPOD_POD_ID" -H "Authorization: Bearer \$RUNPOD_API_KEY"
EOF
chmod +x /root/watchdog.sh
setsid nohup /root/watchdog.sh > /root/watchdog.log 2>&1 < /dev/null &
date -u -d "+$MAX_MINUTES minutes" +"   pod will be deleted at %H:%M UTC"

echo "== 2. system packages (Ollama's installer needs zstd)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq zstd curl lshw > /dev/null

echo "== 3. Ollama $OLLAMA_VERSION, listening on 127.0.0.1 only"
curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=$OLLAMA_VERSION sh > /root/ollama_install.log 2>&1
pkill -x ollama || true
OLLAMA_HOST=127.0.0.1:11434 \
OLLAMA_CONTEXT_LENGTH=4096 \
OLLAMA_NUM_PARALLEL=1 \
OLLAMA_MAX_LOADED_MODELS=3 \
OLLAMA_KEEP_ALIVE=30m \
    setsid nohup ollama serve > /root/ollama.log 2>&1 < /dev/null &
until curl -sf http://127.0.0.1:11434/api/version | grep -q '"version"'; do sleep 1; done
echo "   ollama $(curl -s http://127.0.0.1:11434/api/version)"

echo "== 4. models: $*"
for model in "$@"; do
    ollama pull "$model" > /dev/null 2>&1 && echo "   pulled $model"
done
ollama list
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
