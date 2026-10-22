"""Copy a few garak prompts from the M1 run into attacks/m1_garak_samples.yaml for /demo.

They are only for showing M1 live (and for the "guard blocked" screenshot); M1 results
come from garak's own run. Picked automatically from the chat log:
  - the prompt-injection prompts the guard blocked most often in the run (mildest payload:
    the bot is told to print "I hate humans"; Slurs/Substances prompts are left out on
    purpose, because /demo also shows the answer before the guard)
  - the system-prompt-extraction template whose leak reached the visitor (not blocked by
    the guard) most often (if any)

Usage: .venv/bin/python scripts/make_m1_samples.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detectors  # noqa: E402
from app.settings import ROOT, load_settings  # noqa: E402


def main() -> None:
    settings = load_settings()
    chat = [json.loads(line) for line in (ROOT / "results/midterm/chat_log.jsonl").read_text().splitlines()]

    blocked = Counter(e["user_message"] for e in chat
                      if e.get("attack_id") == "garak:promptinject" and e.get("blocked_by") == "guard")
    leaked = Counter(e["user_message"] for e in chat
                     if e.get("attack_id") == "garak:sysprompt_extraction" and "final_answer" in e
                     and detectors.run_exact_detectors(e["final_answer"], settings.system_prompt,
                                                       settings.detectors)["G1_prompt_leak"])

    attacks = []
    for i, (prompt, n) in enumerate(blocked.most_common(2), 1):
        attacks.append({"id": f"M1-G5-promptinject-{i}", "goal": "G5", "source": "promptinject.HijackHateHumans",
                        "note": f"blocked by the guard in {n} of 5 runs during M1", "prompt": prompt})
    for i, (prompt, n) in enumerate(leaked.most_common(1), 1):
        attacks.append({"id": f"M1-G1-sysprompt-{i}", "goal": "G1", "source": "sysprompt_extraction.SystemPromptExtraction",
                        "note": f"the leak reached the visitor in {n} of 5 runs during M1", "prompt": prompt})

    header = ("# M1 samples for /demo only: real garak prompts copied from the M1 run by\n"
              "# scripts/make_m1_samples.py. M1 results come from the garak run, not from this file.\n")
    body = yaml.safe_dump({"method": "M1", "attacks": attacks}, sort_keys=False, allow_unicode=True, width=100)
    (ROOT / "attacks" / "m1_garak_samples.yaml").write_text(header + body, encoding="utf-8")
    print(f"{len(attacks)} samples written to attacks/m1_garak_samples.yaml")


if __name__ == "__main__":
    main()
