#!/usr/bin/env bash
# Run the baseline and the three proxy modes at the same time.
# Each run is still sequential inside (one request at a time, as garak does with
# Ollama); running them side by side only uses Ollama's 4 parallel slots
# (scripts/start_ollama.sh), so all four modes share the same server and load.
# Ports 8011-8013: on Runpod images ports such as 8001 are taken by nginx.
source "$(dirname "$0")/common.sh"
cd "$ROOT"
mkdir -p results

bash scripts/run_baseline.sh                   > results/run_baseline.log 2>&1 & P1=$!
sleep 5
PORT=8011 bash scripts/run_mitigated.sh none            > results/run_none.log 2>&1 & P2=$!
sleep 5
PORT=8012 bash scripts/run_mitigated.sh sysprompt       > results/run_sysprompt.log 2>&1 & P3=$!
sleep 5
PORT=8013 bash scripts/run_mitigated.sh sysprompt_guard > results/run_sysprompt_guard.log 2>&1 & P4=$!

status=0
for pid in $P1 $P2 $P3 $P4; do
    wait "$pid" || status=1
done
echo "all runs finished, exit status $status"
exit $status
