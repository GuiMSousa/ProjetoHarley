"""Run Reflex event handlers in unit tests the way the Reflex event processor does."""

from __future__ import annotations

import inspect
from typing import Any


def run_event(handler: Any, state: Any, *args: Any, **kwargs: Any) -> Any:
    """Call ``handler.fn`` on ``state`` and return the event it produces.

    Handlers that show a busy state are generators (they ``yield`` before calling Xano so the
    UI renders "Salvando…"). Reflex drains the generator and also processes its ``return``
    value; this helper does the same, so tests read the final state and the returned event.
    """
    result = handler.fn(state, *args, **kwargs)
    if not inspect.isgenerator(result):
        return result
    try:
        while True:
            next(result)
    except StopIteration as stop:
        return stop.value
