#!/bin/bash
# Safety net: delete this pod after 4 hours even if nobody remembers to.
eval "$(tr "\0" "\n" < /proc/1/environ | grep -E "^RUNPOD_(POD_ID|API_KEY)=" | sed "s/^/export /")"
sleep 14400
runpodctl remove pod "$RUNPOD_POD_ID"
