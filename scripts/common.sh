#!/usr/bin/env bash
# Settings shared by every run, so baseline and mitigated runs use exactly
# the same probes, number of generations and seed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${VENV:-$ROOT/.venv}"
GARAK="$VENV/bin/garak"
GARAK_RUNS="${XDG_DATA_HOME:-$HOME/.local/share}/garak/garak_runs"

GENERATIONS=5
SEED=42

# grandma: all 4 active classes (Win10, Win11, Slurs, Substances) - emotional
#   manipulation / storytelling, the "grandma exploit" from Zeng et al.
# dan: 13 classic role-play jailbreaks (inactive by default in garak 0.17,
#   so they are named explicitly) + AutoDANCached (3 pre-generated AutoDAN prompts).
#   Left out: Ablation_Dan_11_0 (127 variants of one prompt), DanInTheWild
#   (only MitigationBypass detector), AutoDAN (needs an external NVIDIA API),
#   ChatGPT_Image_Markdown (markdown exfiltration, not a jailbreak).
PROBES="grandma"
PROBES+=",dan.Dan_6_0,dan.Dan_6_2,dan.Dan_7_0,dan.Dan_8_0,dan.Dan_9_0,dan.Dan_10_0,dan.Dan_11_0"
PROBES+=",dan.DUDE,dan.STAN,dan.DAN_Jailbreak,dan.AntiDAN"
PROBES+=",dan.ChatGPT_Developer_Mode_v2,dan.ChatGPT_Developer_Mode_RANTI,dan.AutoDANCached"

# Copy garak's report files for one run into results/<mode>/
copy_reports() {
    local prefix=$1 dest=$2
    for ext in report.jsonl hitlog.jsonl report.html; do
        if [[ -f "$GARAK_RUNS/$prefix.$ext" ]]; then
            cp "$GARAK_RUNS/$prefix.$ext" "$dest/"
        else
            echo "note: $prefix.$ext not found (hitlog is absent when there are no hits)"
        fi
    done
}
