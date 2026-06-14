from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Base class for user-triggered assistant agents.

    Agents receive compact context and return
    text responses. They do not modify campaign files.
    """

    name: str

    @abstractmethod
    def run(self, *, question: str, context: dict[str, Any]) -> str:
        raise NotImplementedError