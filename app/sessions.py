"""Conversation history per session_id, kept in memory (gone after a restart).

Only what the user actually saw is stored: the user's message and the final
answer after the guard. Old messages and old sessions are dropped so memory
stays bounded.
"""

import threading
from collections import OrderedDict


class SessionStore:
    def __init__(self, max_messages: int = 10, max_sessions: int = 1000):
        self.max_messages = max_messages
        self.max_sessions = max_sessions
        self._sessions: OrderedDict[str, list[dict]] = OrderedDict()
        self._lock = threading.Lock()

    def history(self, session_id: str) -> list[dict]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def add_turn(self, session_id: str, user_message: str, answer: str) -> None:
        with self._lock:
            messages = self._sessions.setdefault(session_id, [])
            messages.append({"role": "user", "content": user_message})
            messages.append({"role": "assistant", "content": answer})
            del messages[: -self.max_messages]          # keep only the last N messages
            self._sessions.move_to_end(session_id)
            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)      # forget the least recently used session
