#!/usr/bin/env bash
# Baseline: garak -> Ollama directly, no proxy and no defence.
source "$(dirname "$0")/common.sh"

PREFIX=baseline
OUT="$ROOT/results/baseline"
mkdir -p "$OUT"
cp "$ROOT/configs/garak_baseline.yaml" "$OUT/garak_config.yaml"   # config used, next to the results

"$GARAK" --config "$OUT/garak_config.yaml" \
    --probes "$PROBES" \
    --generations "$GENERATIONS" \
    --seed "$SEED" \
    --report_prefix "$PREFIX" \
    2>&1 | tee "$OUT/garak_console.log"

copy_reports "$PREFIX" "$OUT"
