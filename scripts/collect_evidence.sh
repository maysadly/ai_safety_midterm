#!/usr/bin/env bash
# Save versions, hardware and the probe/detector catalogue into evidence/.
source "$(dirname "$0")/common.sh"
EVID="$ROOT/evidence"
mkdir -p "$EVID"

nvidia-smi > "$EVID/pod_nvidia-smi.txt"
{ cat /etc/os-release; echo; uname -a; echo; free -h; echo; df -h /; } > "$EVID/pod_system.txt"
"$VENV/bin/python" --version > "$EVID/python_version.txt"

"$GARAK" --version > "$EVID/garak_version.txt" 2>&1
"$GARAK" --help > "$EVID/garak_help.txt" 2>&1
"$GARAK" --list_probes > "$EVID/garak_list_probes.txt" 2>&1
"$GARAK" --list_detectors > "$EVID/garak_list_detectors.txt" 2>&1

ollama --version > "$EVID/ollama_version.txt" 2>&1
ollama list > "$EVID/ollama_list.txt"
ollama show qwen2.5:7b-instruct > "$EVID/ollama_show_qwen2.5.txt"
ollama show --modelfile qwen2.5:7b-instruct > "$EVID/ollama_modelfile_qwen2.5.txt"
ollama show llama-guard3:1b > "$EVID/ollama_show_llama-guard3.txt"

# Default detectors of every probe we run (primary_detector / extended_detectors)
: > "$EVID/probe_plugin_info.txt"
for probe in $("$GARAK" --list_probes 2>/dev/null | grep -oE 'probes\.grandma\.[A-Za-z0-9_]+' | sort -u) \
             $(echo "$PROBES" | tr ',' '\n' | grep '^dan\.' | sed 's/^/probes./'); do
    echo "===== $probe" >> "$EVID/probe_plugin_info.txt"
    "$GARAK" --plugin_info "$probe" >> "$EVID/probe_plugin_info.txt" 2>&1
done
echo "evidence saved to $EVID"
