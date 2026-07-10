"""
memory.py
─────────
Per-user conversation memory.
Stores last 5 turns and tracks the last mentioned symbol
so follow-up questions like "should I buy now?" resolve correctly.
In-process store (no Redis needed for memory — it's per-session).
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Turn:
    prompt:    str
    response:  str
    symbol:    str | None
    intent:    str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ConversationMemory:
    MAX_TURNS = 5

    def __init__(self):
        self._turns: deque[Turn] = deque(maxlen=self.MAX_TURNS)
        self.last_symbol: str | None = None
        self.last_response: str | None = None   # full text of the previous reply

    def add(self, prompt: str, response: str, symbol: str | None, intent: str):
        if symbol:
            self.last_symbol = symbol
        self.last_response = response
        self._turns.append(Turn(prompt=prompt, response=response,
                                symbol=symbol, intent=intent))

    def get_context_symbol(self) -> str | None:
        """Return the most recently discussed symbol."""
        return self.last_symbol

    def get_history(self) -> list[dict]:
        return [{"prompt": t.prompt, "response": t.response} for t in self._turns]

    def clear(self):
        self._turns.clear()
        self.last_symbol = None


# ── Global per-user memory store ──────────────────────────────────────────────
# Key: user_id (str), Value: ConversationMemory
_memories: dict[str, ConversationMemory] = {}


def get_memory(user_id: str) -> ConversationMemory:
    if user_id not in _memories:
        _memories[user_id] = ConversationMemory()
    return _memories[user_id]


def clear_memory(user_id: str):
    if user_id in _memories:
        _memories[user_id].clear()
