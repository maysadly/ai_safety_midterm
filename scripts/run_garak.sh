#!/usr/bin/env bash
# M1: run the garak probe groups against the running app (POST /api/chat).
# The app must already run on 127.0.0.1:8000 with RATE_LIMIT_ENABLED=false.
# garak lives in its own venv (.venv-garak), because it pulls torch/transformers.
#
# Usage:  bash scripts/run_garak.sh                 # all groups
#         bash scripts/run_garak.sh grandma         # one group
# Output: results/midterm/garak/<group>/{garak_config.yaml, garak_console.log, *.report.jsonl, ...}
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GARAK="$ROOT/.venv-garak/bin/garak"
GARAK_RUNS="${XDG_DATA_HOME:-$HOME/.local/share}/garak/garak_runs"

# G5: the probe set of Assignment 2 (16 classic DAN prompts, grandma Slurs + Substances).
#   The classic DAN classes are inactive by default in garak 0.17, so they are named one by one.
# G1: system prompt extraction templates (scored with our exact detectors, see configs/garak_rest.yaml).
# G5: prompt injection that makes the bot print a hateful "rogue string".
declare -A PROBES=(
    [dan]="dan.Dan_6_0,dan.Dan_6_2,dan.Dan_7_0,dan.Dan_8_0,dan.Dan_9_0,dan.Dan_10_0,dan.Dan_11_0,dan.DUDE,dan.STAN,dan.DAN_Jailbreak,dan.AntiDAN,dan.ChatGPT_Developer_Mode_v2,dan.ChatGPT_Developer_Mode_RANTI,dan.AutoDANCached"
    [grandma]="grandma.Slurs,grandma.Substances"
    [sysprompt_extraction]="sysprompt_extraction.SystemPromptExtraction"
    [promptinject]="promptinject.HijackHateHumans"
)
if [[ $# -gt 0 ]]; then
    groups=("$@")
else
    groups=(dan grandma sysprompt_extraction promptinject)
fi

curl -sf http://127.0.0.1:8000/health | grep -q system_prompt_sha256 || { echo "app is not running on :8000"; exit 1; }

for group in "${groups[@]}"; do
    out="$ROOT/results/midterm/garak/$group"
    mkdir -p "$out"
    sed "s/ATTACK_ID/garak:$group/" "$ROOT/configs/garak_rest.yaml" > "$out/garak_config.yaml"
    echo "== $group: ${PROBES[$group]}"
    "$GARAK" --config "$out/garak_config.yaml" \
        --probes "${PROBES[$group]}" \
        --report_prefix "midterm_$group" \
        2>&1 | tee "$out/garak_console.log"
    for ext in report.jsonl hitlog.jsonl report.html; do
        cp "$GARAK_RUNS/midterm_$group.$ext" "$out/" 2>/dev/null || echo "note: midterm_$group.$ext not found"
    done
done
