"""Minimal client for the Ollama chat API (POST /api/chat, no streaming).

The gateway only needs one method, chat(). Tests replace this class with a fake
object that has the same method, so no Ollama is needed to run them.
"""

import httpx


class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 300):
        self.http = httpx.Client(base_url=base_url, timeout=timeout)

    def chat(self, model: str, messages: list[dict], options: dict, format: str | None = None) -> str:
        body = {"model": model, "messages": messages, "options": options, "stream": False}
        if format:
            body["format"] = format  # "json" makes Ollama return valid JSON (used by the judge)
        response = self.http.post("/api/chat", json=body)
        response.raise_for_status()
        return response.json()["message"]["content"]
