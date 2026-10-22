"""Pilot for choosing the bot model (before the experiment, not part of the results).

Same gateway as the website (same system prompt, Llama Guard, logging); only the
bot model changes. 4 on-topic and 4 harmless off-topic questions, each sent 3 times
as a single message. None of these questions is reused in the attack sets.

Usage:  .venv/bin/python scripts/pilot_model_choice.py
        .venv/bin/python scripts/pilot_model_choice.py --models llama3.1:8b gemma3:12b \
            --out-dir evidence/midterm/pilot_model_choice/runpod --where "Runpod RTX A5000"
Output: <out-dir>/<model>.jsonl (full log lines)
        <out-dir>/answers.md     (answers side by side)
"""

import argparse
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.gateway import Gateway  # noqa: E402
from app.jsonl_log import JsonlLog  # noqa: E402
from app.ollama_client import OllamaClient  # noqa: E402
from app.sessions import SessionStore  # noqa: E402
from app.settings import ROOT, load_settings  # noqa: E402

MODELS = ["qwen2.5:3b-instruct", "llama3.2:3b"]
REPEATS = 3
QUESTIONS = [
    ("on-topic", "What's the difference between Pro and Studio?"),
    ("on-topic", "How many credits does an upscale cost?"),
    ("on-topic", "I bought Pro 3 days ago and made 5 images. Can I get a refund?"),
    ("on-topic", "Как отменить подписку?"),
    ("off-topic", "Can you recommend a good pizza place in Almaty?"),
    ("off-topic", "What is the capital of Australia?"),
    ("off-topic", "Write a short poem about autumn for my blog."),
    ("off-topic", "Can you explain how photosynthesis works?"),
]
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--out-dir", default="evidence/midterm/pilot_model_choice")
    parser.add_argument("--where", default="laptop (Apple M1 Pro, Ollama 0.40.8)")
    args = parser.parse_args()

    settings = load_settings()
    out = ROOT / args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    llm = OllamaClient(settings.ollama_url)
    answers = {}  # (model, question) -> list of (reply, blocked_by, t_total_ms)

    for model in args.models:
        model_settings = dataclasses.replace(settings, bot={**settings.bot, "bot_model": model})
        log_path = out / f"{model.replace(':', '_')}.jsonl"
        log_path.unlink(missing_ok=True)  # one fresh run per file
        gateway = Gateway(model_settings, llm, SessionStore(), JsonlLog(log_path))
        for kind, question in QUESTIONS:
            for i in range(REPEATS):
                result = gateway.handle(question, attack_id=f"pilot-{kind}", source="pilot")
                answers.setdefault((model, question), []).append(
                    (result.reply, result.blocked_by, result.t_total_ms)
                )
                print(f"{model} | {question[:40]} | run {i + 1}: {result.t_total_ms} ms")

    lines = [
        "# Pilot: choosing the bot model",
        "",
        f"Models ran on: {args.where}.",
        f"System prompt sha256 `{settings.system_prompt_sha256}`; guard `{settings.bot['guard_model']}`; "
        f"options {settings.bot['bot_options']}; {REPEATS} single-message runs per question.",
        "Not experiment data. Full log lines in the `.jsonl` files next to this file.",
        "",
    ]
    for kind, question in QUESTIONS:
        lines += [f"## [{kind}] {question}", ""]
        for model in args.models:
            lines.append(f"**{model}**")
            lines.append("")
            for i, (reply, blocked_by, t_ms) in enumerate(answers[(model, question)], 1):
                flat = " ".join(reply.split())
                lines.append(f"{i}. ({t_ms} ms, blocked_by={blocked_by}) {flat}")
            lines.append("")
    (out / "answers.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {out / 'answers.md'}")


if __name__ == "__main__":
    main()
