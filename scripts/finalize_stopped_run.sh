#!/usr/bin/env bash
# For a garak run that was stopped before the end (we stopped every run right
# after grandma.Substances was evaluated and skipped Win10/Win11):
# copy its report files into results/<mode>/ and build the HTML report that
# garak normally writes only when a run finishes.
# Usage: bash scripts/finalize_stopped_run.sh baseline|none|sysprompt|sysprompt_guard
source "$(dirname "$0")/common.sh"

MODE=${1:?usage: finalize_stopped_run.sh <mode>}
OUT="$ROOT/results/$MODE"
mkdir -p "$OUT"

copy_reports "$MODE" "$OUT"
"$VENV/bin/python" -m garak.analyze.report_digest \
    --report_path "$OUT/$MODE.report.jsonl" \
    --output_path "$OUT/$MODE.report.html"
