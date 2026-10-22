#!/usr/bin/env bash
# One-time setup on a fresh Runpod pod (image runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404,
# Ubuntu 24.04, Python 3.12, NVIDIA GPU). Run from anywhere: bash scripts/setup_pod.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== 1. system packages (zstd is needed by the Ollama installer)"
apt-get update -qq
apt-get install -y -qq zstd curl > /dev/null

echo "== 2. Ollama: install, start the server, pull the models"
curl -fsSL https://ollama.com/install.sh | sh
bash scripts/start_ollama.sh
ollama pull qwen2.5:7b-instruct
ollama pull llama-guard3:1b

echo "== 3. Python venv: garak (official install: pip install -U garak) + proxy deps"
python3 -m venv .venv
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q -U garak fastapi uvicorn httpx
.venv/bin/pip freeze > requirements.lock

echo "== done. Next: bash scripts/collect_evidence.sh"
