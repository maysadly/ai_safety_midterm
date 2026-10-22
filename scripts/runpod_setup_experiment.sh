#!/usr/bin/env bash
# Runs ON the experiment pod, inside the copied repository (e.g. /root/midterm).
# 1. Ollama + models (scripts/runpod_setup_ollama.sh, incl. watchdog)
# 2. venv for the app (.venv) and a separate venv for garak (.venv-garak)
# 3. a fresh .env with random secrets (secrets never leave this pod), rate limit off
# 4. versions and hardware into evidence/midterm/pod/
#
# Usage (from the laptop):  ssh pod 'cd /root/midterm && MAX_MINUTES=150 bash scripts/runpod_setup_experiment.sh'
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

MODELS="llama3.1:8b llama-guard3:1b qwen2.5:7b-instruct qwen2.5:32b-instruct"
bash scripts/runpod_setup_ollama.sh $MODELS

echo "== 5. app venv"
python3 -m venv .venv
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q -r requirements.txt

echo "== 6. garak venv (garak 0.17.0, same version as Assignment 2)"
python3 -m venv .venv-garak
.venv-garak/bin/pip install -q -U pip
.venv-garak/bin/pip install -q garak==0.17.0

echo "== 7. .env for the experiment"
random() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }
cat > .env <<EOF
ADMIN_PASSWORD=$(random 12)
COOKIE_SECRET=$(random 32)
IP_HASH_SALT=$(random 16)
OLLAMA_URL=http://127.0.0.1:11434
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MINUTE=10
DEBUG_LINES=false
CHAT_LOG_PATH=results/midterm/chat_log.jsonl
EVAL_LOG_PATH=results/midterm/evaluations.jsonl
EOF
chmod 600 .env

echo "== 8. evidence"
mkdir -p evidence/midterm/pod
{
    nvidia-smi
    echo; python3 --version
    echo "ollama $(ollama --version 2>&1 | tail -1)"
    echo; ollama list
    echo; .venv-garak/bin/garak --version 2>&1 | head -3
} > evidence/midterm/pod/system.txt 2>&1
.venv/bin/pip freeze > evidence/midterm/pod/requirements_app.lock
.venv-garak/bin/pip freeze > evidence/midterm/pod/requirements_garak.lock
for m in $MODELS; do
    ollama show "$m" > "evidence/midterm/pod/ollama_show_${m//:/_}.txt"
done
echo "== setup done"
