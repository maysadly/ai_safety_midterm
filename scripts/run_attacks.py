"""Run the fixed attack sets (M0, M2) against the running app, REPEATS times each.

For every attempt it makes the same two calls as the /demo page:
    POST /api/chat           {message, attack_id, source: "runner"}   (single message, no history)
    POST /api/demo/evaluate  {request_id}                             (scores it from the chat log)
and appends one line per attempt to the output file. Attempts already in the file are
skipped, so an interrupted run can simply be started again.

Order: all attacks once (repeat 1), then all again (repeat 2), ... so a run stopped early
still has every attack the same number of times.

Usage (app running with RATE_LIMIT_ENABLED=false):
    .venv/bin/python scripts/run_attacks.py --url http://127.0.0.1:8000 --repeats 5 \
        --out results/midterm/attacks/attempts.jsonl
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.attacks import load_attacks  # noqa: E402
from app.settings import ROOT, load_settings  # noqa: E402


def post(http: httpx.Client, url: str, body: dict) -> dict:
    for attempt in range(3):  # Ollama can be briefly busy loading a model
        response = http.post(url, json=body)
        if response.status_code < 500:
            response.raise_for_status()
            return response.json()
        time.sleep(5 * (attempt + 1))
    response.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--methods", nargs="+", default=["M0", "M2"])
    parser.add_argument("--out", default="results/midterm/attacks/attempts.jsonl")
    args = parser.parse_args()

    settings = load_settings()
    attacks = [a for a in load_attacks() if a["method"] in args.methods]
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            row = json.loads(line)
            done.add((row["attack_id"], row["repeat"]))

    with httpx.Client(base_url=args.url, timeout=600) as http:
        health = http.get("/health").json()
        if health["system_prompt_sha256"] != settings.system_prompt_sha256:
            sys.exit("The server uses a different system prompt than configs/system_prompt.txt - stop.")
        http.post("/admin/login", json={"password": settings.admin_password}).raise_for_status()

        total = len(attacks) * args.repeats
        n = len(done)
        print(f"{len(attacks)} attacks x {args.repeats} repeats = {total} attempts, {n} already done")
        for repeat in range(1, args.repeats + 1):
            for attack in attacks:
                if (attack["id"], repeat) in done:
                    continue
                chat = post(http, "/api/chat",
                            {"message": attack["prompt"], "attack_id": attack["id"], "source": "runner"})
                record = post(http, "/api/demo/evaluate", {"request_id": chat["request_id"]})
                row = {"repeat": repeat, "bot_model": health["bot_model"], "reply": chat["reply"], **record}
                with out.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1
                print(f"[{n}/{total}] r{repeat} {attack['id']}: violated={record['model_violated']} "
                      f"blocked={record['blocked_by']} success={record['attack_success']} "
                      f"({record['chat']['t_total_ms']} ms)", flush=True)


if __name__ == "__main__":
    main()
