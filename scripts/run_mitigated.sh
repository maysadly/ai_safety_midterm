#!/usr/bin/env bash
# Mitigated run: garak -> proxy (in the given mode) -> Ollama.
# Same probes, generations and seed as the baseline (scripts/common.sh).
# Usage: bash scripts/run_mitigated.sh none|sysprompt|sysprompt_guard
#        PORT=8001 bash scripts/run_mitigated.sh sysprompt   # other port, for parallel runs
source "$(dirname "$0")/common.sh"

MODE=${1:?usage: run_mitigated.sh none|sysprompt|sysprompt_guard}
PORT=${PORT:-8000}
OUT="$ROOT/results/$MODE"
mkdir -p "$OUT" "$ROOT/results/proxy_logs"

# Start from an empty proxy log for this mode, so it matches this garak run only.
rm -f "$ROOT/results/proxy_logs/$MODE.jsonl"

PROXY_MODE=$MODE "$VENV/bin/uvicorn" proxy.app:app --app-dir "$ROOT" \
    --host 127.0.0.1 --port "$PORT" > "$OUT/proxy_console.log" 2>&1 &
PROXY_PID=$!
trap 'kill $PROXY_PID 2>/dev/null' EXIT

# Wait until our proxy answers and reports the expected mode. Checking the mode
# matters: on Runpod images some ports (e.g. 8001) already belong to nginx.
proxy_ready=no
for _ in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:$PORT/health" | grep -q "\"mode\":\"$MODE\""; then
        proxy_ready=yes
        break
    fi
    sleep 1
done
if [[ $proxy_ready != yes ]]; then
    echo "proxy in mode $MODE did not start on port $PORT (see $OUT/proxy_console.log)"
    exit 1
fi

# The exact garak config of this run (proxy port filled in) is kept next to the results.
sed "s#127.0.0.1:8000#127.0.0.1:$PORT#" "$ROOT/configs/garak_proxy.yaml" > "$OUT/garak_config.yaml"

"$GARAK" --config "$OUT/garak_config.yaml" \
    --probes "$PROBES" \
    --generations "$GENERATIONS" \
    --seed "$SEED" \
    --report_prefix "$MODE" \
    2>&1 | tee "$OUT/garak_console.log"

copy_reports "$MODE" "$OUT"
