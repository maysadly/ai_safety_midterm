"""The chat gateway. Every message - from the website widget, /demo, garak or
scripts/chat_cli.py - goes through Gateway.handle():

    message -> build_messages(): system prompt + session history + message
            -> bot model (qwen2.5:3b-instruct in Ollama)
            -> check_output(): output guard (Llama Guard 3 1B); "unsafe" => fixed refusal
            -> one line in the chat log (JSONL)
            -> reply

The architecture is fixed for the whole experiment. The final project will add
retrieval (RAG) and tools as extra steps between build_messages() and the bot
call; none of that exists yet.
"""

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.jsonl_log import JsonlLog
from app.sessions import SessionStore
from app.settings import Settings

# Shown instead of an answer the guard calls unsafe. Contains "I'm sorry, but I can",
# a phrase garak's mitigation.MitigationBypass detector counts as a refusal (as in A2).
REFUSAL = "I'm sorry, but I can't help with that request."


class BotUnavailable(Exception):
    """The bot model could not be reached (Ollama down, timeout, ...)."""


@dataclass
class ChatResult:
    request_id: str
    reply: str
    blocked_by: str | None   # None, "guard" or "guard_error"
    guard_verdict: str
    t_model_ms: int
    t_guard_ms: int
    t_total_ms: int


def _ms(seconds: float) -> int:
    return round(seconds * 1000)


class Gateway:
    def __init__(self, settings: Settings, llm, sessions: SessionStore, chat_log: JsonlLog):
        self.settings = settings
        self.llm = llm            # OllamaClient, or a fake in tests
        self.sessions = sessions
        self.chat_log = chat_log

    def build_messages(self, history: list[dict], message: str) -> list[dict]:
        """The system prompt is always first; the user cannot remove or replace it."""
        return (
            [{"role": "system", "content": self.settings.system_prompt}]
            + history
            + [{"role": "user", "content": message}]
        )

    def check_output(self, message: str, answer: str) -> str:
        """Ask Llama Guard 3 about the bot's answer to this message.

        Returns its raw verdict: "safe", or "unsafe" plus a category code like "S2".
        Only the last user message and the answer are sent, as in Assignment 2.
        """
        conversation = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ]
        bot = self.settings.bot
        return self.llm.chat(bot["guard_model"], conversation, bot["guard_options"]).strip()

    def handle(
        self,
        message: str,
        session_id: str | None = None,
        attack_id: str | None = None,
        source: str = "api",
        client_ip_hash: str = "",
    ) -> ChatResult:
        started = time.perf_counter()
        bot = self.settings.bot
        # No session_id = single message without history (how garak talks to us).
        history = self.sessions.history(session_id) if session_id else []
        messages = self.build_messages(history, message)

        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "request_id": uuid.uuid4().hex,
            "source": source,
            "session_id": session_id,
            "attack_id": attack_id,
            "client_ip_hash": client_ip_hash,
            "user_message": message,
            "history_messages": len(history),
            "system_prompt_sha256": self.settings.system_prompt_sha256,
            "bot_model": bot["bot_model"],
            "guard_model": bot["guard_model"],
            "bot_options": bot["bot_options"],
        }

        try:
            model_answer = self.llm.chat(bot["bot_model"], messages, bot["bot_options"])
        except Exception as error:
            entry.update(error=f"bot: {error!r}", t_total_ms=_ms(time.perf_counter() - started))
            self.chat_log.write(entry)
            raise BotUnavailable(str(error)) from error
        model_done = time.perf_counter()

        try:
            guard_verdict = self.check_output(message, model_answer)
            blocked_by = "guard" if guard_verdict.lower().startswith("unsafe") else None
        except Exception as error:
            # Fail closed: if the guard cannot check the answer, the answer is not shown.
            guard_verdict = f"error: {error!r}"
            blocked_by = "guard_error"
        guard_done = time.perf_counter()

        final_answer = REFUSAL if blocked_by else model_answer
        if session_id:
            self.sessions.add_turn(session_id, message, final_answer)

        result = ChatResult(
            request_id=entry["request_id"],
            reply=final_answer,
            blocked_by=blocked_by,
            guard_verdict=guard_verdict,
            t_model_ms=_ms(model_done - started),
            t_guard_ms=_ms(guard_done - model_done),
            t_total_ms=_ms(time.perf_counter() - started),
        )
        entry.update(
            model_answer=model_answer,   # before the guard
            guard_verdict=guard_verdict,
            blocked_by=blocked_by,
            final_answer=final_answer,   # what the user saw
            t_model_ms=result.t_model_ms,
            t_guard_ms=result.t_guard_ms,
            t_total_ms=result.t_total_ms,
        )
        self.chat_log.write(entry)
        return result
