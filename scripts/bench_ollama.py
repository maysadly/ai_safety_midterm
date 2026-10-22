"""Measure how fast the local Ollama models run on this machine.

For every model: one warm-up request (loads the model into memory), then
RUNS timed requests. Ollama itself reports token counts and durations in
nanoseconds; we only convert them.

Usage:  python scripts/bench_ollama.py [--runs 3] [--out evidence/midterm/model_speed.txt]
Only the standard library is used, so it runs without the project venv.
"""

import argparse
import json
import platform
import statistics
import time
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"

# (model, prompt, options) - options mirror how each model is used in the project.
CASES = [
    (
        "qwen2.5:3b-instruct",
        "In about 150 words, explain what a monthly subscription for an online "
        "AI image generation service could include.",
        {"temperature": 0.7, "top_k": 20, "num_predict": 256},
    ),
    (
        "llama-guard3:1b",
        None,  # guard gets a user/assistant pair, see guard_messages()
        {"temperature": 0, "num_predict": 20},
    ),
    (
        "qwen2.5:7b-instruct",
        "You are a strict evaluator. Did the following answer promise a free upgrade? "
        "Answer: 'Sure, I upgraded your plan to Pro for free.' Reply with YES or NO and "
        "one sentence of reasoning.",
        {"temperature": 0, "num_predict": 64},
    ),
]


def guard_messages() -> list[dict]:
    return [
        {"role": "user", "content": "How many images can I generate on the Free plan?"},
        {"role": "assistant", "content": "The Free plan includes 25 image credits per month."},
    ]


def chat(model: str, messages: list[dict], options: dict) -> dict:
    body = json.dumps(
        {"model": model, "messages": messages, "options": options, "stream": False}
    ).encode()
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read())


def bench(model: str, prompt: str | None, options: dict, runs: int) -> list[str]:
    messages = guard_messages() if prompt is None else [{"role": "user", "content": prompt}]

    started = time.time()
    warmup = chat(model, messages, options)
    lines = [
        f"## {model}",
        f"warm-up (includes loading): wall {time.time() - started:.2f} s, "
        f"load_duration {warmup.get('load_duration', 0) / 1e9:.2f} s",
    ]

    gen_speeds, walls = [], []
    for i in range(runs):
        started = time.time()
        r = chat(model, messages, options)
        wall = time.time() - started
        tokens = r.get("eval_count", 0)
        gen_s = r.get("eval_duration", 1) / 1e9
        prompt_tokens = r.get("prompt_eval_count", 0)
        prompt_s = r.get("prompt_eval_duration", 1) / 1e9
        gen_speeds.append(tokens / gen_s)
        walls.append(wall)
        lines.append(
            f"run {i + 1}: wall {wall:.2f} s | prompt {prompt_tokens} tok in {prompt_s:.2f} s | "
            f"generated {tokens} tok, {tokens / gen_s:.1f} tok/s"
        )
    lines.append(
        f"median: {statistics.median(gen_speeds):.1f} tok/s generation, "
        f"{statistics.median(walls):.2f} s wall per request"
    )
    lines.append(f"last answer (first 200 chars): {r['message']['content'][:200]!r}")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out", default=None, help="also write the report to this file")
    parser.add_argument("--models", nargs="*", help="only these models (default: all)")
    args = parser.parse_args()

    report = [
        f"# Ollama speed on {platform.machine()} / {platform.platform()}",
        f"# measured {time.strftime('%Y-%m-%d %H:%M:%S %Z')}, requests sent one at a time",
        "",
    ]
    for model, prompt, options in CASES:
        if args.models and model not in args.models:
            continue
        report += [f"options: {options}"] + bench(model, prompt, options, args.runs) + [""]

    text = "\n".join(report)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
