"""Backup demo: chat with the bot from the terminal through the same POST /api/chat.

Usage (server must be running):
    .venv/bin/python scripts/chat_cli.py                 # one conversation (session)
    .venv/bin/python scripts/chat_cli.py --debug         # also print guard verdict and latency
    .venv/bin/python scripts/chat_cli.py --url http://127.0.0.1:8000

The --debug details come from the server only when "debug lines" are on in /admin.
"""

import argparse
import uuid

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--debug", action="store_true", help="print the debug details if the server sends them")
    args = parser.parse_args()

    session_id = uuid.uuid4().hex
    print(f"Chatting with Kiln at {args.url} (session {session_id[:8]}). Empty line or Ctrl+C to quit.")
    with httpx.Client(base_url=args.url, timeout=300) as http:
        while True:
            try:
                message = input("\nyou> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not message:
                break
            response = http.post(
                "/api/chat", json={"message": message, "session_id": session_id, "source": "cli"}
            )
            if response.status_code != 200:
                print(f"[{response.status_code}] {response.json().get('detail')}")
                continue
            data = response.json()
            print(f"kiln> {data['reply']}")
            if args.debug and "debug" in data:
                print(f"      [debug] {data['debug']}")


if __name__ == "__main__":
    main()
