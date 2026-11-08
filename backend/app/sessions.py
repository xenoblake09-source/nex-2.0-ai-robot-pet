"""In-memory session store.

Keeps a short conversation window plus a couple of durable little facts (the
user's name) per session id. Purely in-memory on purpose: NEX does not need
to store personal data across restarts for an exhibition demo.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock

from .config import get_settings

MAX_TURNS = 24
MAX_FACTS = 12
SESSION_TTL = 60 * 60 * 6  # 6 hours


@dataclass
class Session:
    session_id: str
    turns: list[dict[str, str]] = field(default_factory=list)
    recent_replies: list[str] = field(default_factory=list)
    facts: dict[str, str] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})
        if len(self.turns) > MAX_TURNS:
            self.turns = self.turns[-MAX_TURNS:]

    def add_reply(self, reply: str) -> None:
        self.recent_replies.append(reply[:200])
        if len(self.recent_replies) > 6:
            self.recent_replies = self.recent_replies[-6:]

    def set_fact(self, key: str, value: str) -> None:
        self.facts[key] = value
        if len(self.facts) > MAX_FACTS:
            for old in list(self.facts)[: len(self.facts) - MAX_FACTS]:
                self.facts.pop(old, None)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def _prune(self) -> None:
        cutoff = time.time() - SESSION_TTL
        stale = [sid for sid, s in self._sessions.items() if s.updated_at < cutoff]
        for sid in stale:
            self._sessions.pop(sid, None)

    def get(self, session_id: str) -> Session:
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id)
            if session is None:
                session = Session(session_id=session_id)
                self._sessions[session_id] = session
            session.updated_at = time.time()
            return session

    def drop(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


sessions = SessionStore()


def history_window(session: Session) -> list[dict[str, str]]:
    settings = get_settings()
    limit = settings.history_turns * 2
    return session.turns[-limit:]
