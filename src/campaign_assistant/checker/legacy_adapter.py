from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from campaign_assistant.checker.schema import TTMSTRUCTURE


@dataclass(slots=True)
class LegacyCheckAdapter:
    checker: object

    def runners(self) -> dict[str, Callable[[], None]]:
        """
        Expose only the legacy-backed checks that still remain in use.
        """
        return {
            TTMSTRUCTURE: self._run_ttm,
        }

    def _run_ttm(self) -> None:
        self.checker.checkTTMStructure()