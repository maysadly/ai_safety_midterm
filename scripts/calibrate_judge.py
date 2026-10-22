"""Check the LLM judge on hand-labelled answers (attacks/judge_calibration.yaml).

Decision rule, fixed before running: the experiment uses the judge model with the higher
accuracy on this set; on a tie, the larger model.

Usage:  OLLAMA_URL=http://127.0.0.1:11434 .venv/bin/python scripts/calibrate_judge.py \
            qwen2.5:7b-instruct qwen2.5:32b-instruct
Output: evidence/midterm/judge_calibration/<model>.jsonl (every verdict)
        evidence/midterm/judge_calibration/summary.md
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.judge import Judge  # noqa: E402
from app.ollama_client import OllamaClient  # noqa: E402
from app.settings import ROOT, load_settings  # noqa: E402

OUT = ROOT / "evidence" / "midterm" / "judge_calibration"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("models", nargs="+")
    args = parser.parse_args()

    settings = load_settings()
    items = yaml.safe_load((ROOT / "attacks" / "judge_calibration.yaml").read_text())["items"]
    llm = OllamaClient(settings.ollama_url)
    OUT.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Judge calibration",
        "",
        f"{len(items)} hand-written answers (attacks/judge_calibration.yaml), options "
        f"{settings.bot['judge_options']}. Decision rule fixed before the run: higher accuracy wins, "
        "tie -> larger model.",
        "",
        "| judge model | correct | accuracy | false positives | false negatives | invalid JSON | wrong items |",
        "|---|---|---|---|---|---|---|",
    ]
    for model in args.models:
        judge = Judge(llm, model, settings.bot["judge_options"])
        judge.judge("G3", "warm-up", "warm-up")  # load the model before timing anything
        rows, wrong = [], []
        fp = fn = invalid = 0
        for item in items:
            result = judge.judge(item["goal"], item["message"], item["answer"])
            rows.append({**item, **result})
            if result["violation"] is None:
                invalid += 1
                wrong.append(item["id"])
            elif result["violation"] != item["expected"]:
                wrong.append(item["id"])
                fp += result["violation"] and not item["expected"]
                fn += item["expected"] and not result["violation"]
            print(f"{model} {item['id']}: expected {item['expected']}, got {result['violation']}")
        with (OUT / f"{model.replace(':', '_')}.jsonl").open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        correct = len(items) - len(wrong)
        lines.append(
            f"| {model} | {correct}/{len(items)} | {correct / len(items):.2f} | {fp} | {fn} | {invalid} | "
            f"{', '.join(wrong) or '-'} |"
        )

    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
