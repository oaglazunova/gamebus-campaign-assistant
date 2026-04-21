from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class LegacyCheckAdapter:
    checker: object

    def runners(self) -> dict[str, Callable[[], None]]:
        """
        Legacy execution is no longer used for checker runs.

        The wrapper still borrows the legacy workbook loader for now,
        but all checks are executed through native implementations.
        """
        return {}