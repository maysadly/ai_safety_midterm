#!/bin/bash
# Stop each garak run as soon as grandma.Substances has been evaluated (Win10/Win11 skipped).
RUNS=/root/.local/share/garak/garak_runs
left="baseline none sysprompt sysprompt_guard"
while [ -n "$left" ]; do
  next=""
  for m in $left; do
    if grep -q "\"entry_type\": \"eval\", \"probe\": \"grandma.Substances\"" $RUNS/$m.report.jsonl; then
      first=${m:0:1}; rest=${m:1}
      pkill -f "results/[$first]$rest/garak_config"
      echo "$(date -u +%T) stopped $m"
    else
      next="$next $m"
    fi
  done
  left=$(echo $next)
  sleep 3
done
echo "$(date -u +%T) all stopped"
