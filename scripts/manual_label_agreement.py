"""Compare the student's manual labels with the automatic verdicts.

Fill the `my_label` column of results/midterm/manual_labeling.csv first:
    yes / true / 1  = the answer breaks the rule of its goal (violation)
    no / false / 0  = it does not
Empty rows are skipped. Then run:
    .venv/bin/python scripts/manual_label_agreement.py
Output: results/midterm/manual_label_agreement.md (per automatic source: detectors, judge, garak)
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "results" / "midterm" / "manual_labeling.csv"
OUT = ROOT / "results" / "midterm" / "manual_label_agreement.md"

YES, NO = {"yes", "y", "true", "1", "violation"}, {"no", "n", "false", "0"}


def parse(label: str) -> bool | None:
    label = label.strip().lower()
    return True if label in YES else False if label in NO else None


def agreement(rows: list[dict]) -> dict:
    """{auto_source: {"labelled", "agree", "auto_fp", "auto_fn"}} for rows with a manual label."""
    stats = defaultdict(lambda: {"labelled": 0, "agree": 0, "auto_fp": 0, "auto_fn": 0})
    for r in rows:
        mine = parse(r["my_label"])
        if mine is None:
            continue
        auto = r["auto_violation"] == "True"
        for key in (r["auto_source"], "all"):
            s = stats[key]
            s["labelled"] += 1
            s["agree"] += auto == mine
            s["auto_fp"] += auto and not mine   # automatic: violation, student: no
            s["auto_fn"] += mine and not auto   # automatic: no violation, student: violation
    return dict(stats)


def main() -> None:
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    stats = agreement(rows)
    if not stats:
        sys.exit("No manual labels yet: fill the my_label column (yes/no) first.")
    lines = ["# Manual labels vs automatic verdicts", "",
             f"From `{CSV.relative_to(ROOT)}` ({sum(s['labelled'] for k, s in stats.items() if k != 'all')} labelled rows).", "",
             "| automatic source | labelled | agree | automatic said violation, student no | automatic said no, student violation |",
             "|---|---|---|---|---|"]
    for key in sorted(stats, key=lambda k: (k == "all", k)):
        s = stats[key]
        lines.append(f"| {key} | {s['labelled']} | {s['agree']} ({100 * s['agree'] / s['labelled']:.0f}%) | "
                     f"{s['auto_fp']} | {s['auto_fn']} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
