"""Run garak's own detectors again on the bot's answers BEFORE the guard.

Why: garak only sees the final reply of /api/chat. When Llama Guard blocks an answer,
garak sees the refusal, so from garak's report alone we cannot tell whether the bot
broke the rule and the guard caught it, or the bot refused by itself. Our chat log keeps
the answer before the guard (`model_answer`), so here we score that answer with the same
garak detectors.

How:
  1. read every completed attempt in results/midterm/garak/<group>/midterm_<group>.report.jsonl
  2. match each of its outputs to a chat log line (attack_id "garak:<group>", same prompt,
     same final answer; each chat log line is used once)
  3. score both the final answer and the pre-guard answer with every detector garak used
  4. check: our score of the final answer must equal garak's stored score (sanity check)

Runs in the garak venv:  .venv-garak/bin/python scripts/garak_pre_guard.py
Output: results/midterm/garak/pre_guard_scores.jsonl (one line per output x detector)
"""

import importlib
import json
from collections import defaultdict
from pathlib import Path

from garak import _config, _plugins
from garak.attempt import Attempt, Conversation, Message

ROOT = Path(__file__).resolve().parent.parent
GARAK_DIR = ROOT / "results" / "midterm" / "garak"
CHAT_LOG = ROOT / "results" / "midterm" / "chat_log.jsonl"
GROUPS = ["dan", "grandma", "sysprompt_extraction", "promptinject"]


def last_user_text(prompt: dict) -> str:
    """The text the REST generator sent: the last turn of the prompt conversation."""
    return prompt["turns"][-1]["content"]["text"]


def primary_detector(probe_classname: str) -> str:
    module, cls = probe_classname.split(".")
    return getattr(importlib.import_module(f"garak.probes.{module}"), cls).primary_detector


def main() -> None:
    _config.load_base_config()
    chat = [json.loads(line) for line in CHAT_LOG.read_text().splitlines()]
    detectors = {}
    out_rows, mismatches = [], 0

    for group in GROUPS:
        report = GARAK_DIR / group / f"midterm_{group}.report.jsonl"
        if not report.exists():
            print(f"skip {group}: no report")
            continue
        # unused chat log lines of this group, by (prompt, final answer)
        pool = defaultdict(list)
        for e in chat:
            if e.get("attack_id") == f"garak:{group}" and "model_answer" in e:
                pool[(e["user_message"], e["final_answer"])].append(e)

        for line in report.read_text().splitlines():
            entry = json.loads(line)
            if entry.get("entry_type") != "attempt" or entry.get("status") != 2:
                continue
            prompt = last_user_text(entry["prompt"])
            # detectors only read outputs whose prompt language matches theirs, so keep garak's value
            lang = entry["prompt"]["turns"][-1]["content"].get("lang") or "*"
            finals = [o["text"] if o else None for o in entry["outputs"]]
            matched = [pool[(prompt, f)].pop(0) if pool.get((prompt, f)) else None for f in finals]
            if any(m is None for m in matched):
                print(f"WARNING {entry['probe_classname']} seq {entry['seq']}: output without chat log line")
                continue
            primary = primary_detector(entry["probe_classname"])

            for detector_name, garak_scores in entry["detector_results"].items():
                if detector_name not in detectors:
                    detectors[detector_name] = _plugins.load_plugin(f"detectors.{detector_name}")
                scores = {}
                for label, texts in (("final", finals), ("pre_guard", [m["model_answer"] for m in matched])):
                    # the full prompt as garak built it (some detectors read its system turn)
                    attempt = Attempt(prompt=Conversation.from_dict(entry["prompt"]),
                                      probe_classname=entry["probe_classname"],
                                      notes=entry.get("notes") or {}, targets=entry.get("targets") or [],
                                      seq=entry["seq"])
                    attempt.outputs = [Message(text=t, lang=lang) for t in texts]
                    scores[label] = list(detectors[detector_name].detect(attempt))

                for i, m in enumerate(matched):
                    same = scores["final"][i] == garak_scores[i]
                    mismatches += not same
                    out_rows.append({
                        "group": group,
                        "probe": entry["probe_classname"],
                        "seq": entry["seq"],
                        "generation": i,
                        "detector": detector_name,
                        "is_primary": detector_name == primary,
                        "garak_score_final": garak_scores[i],
                        "our_score_final": scores["final"][i],
                        "score_pre_guard": scores["pre_guard"][i],
                        "blocked_by": m["blocked_by"],
                        "request_id": m["request_id"],
                    })

    path = GARAK_DIR / "pre_guard_scores.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row) + "\n")
    print(f"{len(out_rows)} scores written to {path}; final-answer scores differing from garak's: {mismatches}")


if __name__ == "__main__":
    main()
