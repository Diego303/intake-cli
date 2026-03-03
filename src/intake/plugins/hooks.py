"""Pipeline hook system for plugin extensibility.

Provides an event bus that plugins can subscribe to for receiving
notifications about pipeline events (e.g. pre_parse, post_generate).

This is intentionally minimal in Phase 1. The infrastructure is ready
but no hook emissions are wired into the pipeline yet.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class HookEvent:
    """An event emitted during the pipeline.

    Attributes:
        name: Event identifier (e.g. "pre_parse", "post_generate").
        data: Arbitrary event payload.
    """

    name: str
    data: dict[str, object] = field(default_factory=dict)


HookCallback = Callable[[HookEvent], None]


class HookManager:
    """Manages pipeline hooks for plugin extensibility.

    Plugins register callbacks for specific event names. When the pipeline
    emits an event, all registered callbacks are called in registration order.

    Example::

        hooks = HookManager()
        hooks.register("post_parse", lambda event: print(event.data))
        hooks.emit(HookEvent(name="post_parse", data={"source": "req.md"}))
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[HookCallback]] = defaultdict(list)

    def register(self, event_name: str, callback: HookCallback) -> None:
        """Register a callback for a pipeline event.

        Args:
            event_name: Event to listen for.
            callback: Function to call when the event is emitted.
        """
        self._hooks[event_name].append(callback)
        logger.debug("hook_registered", event_name=event_name)

    def emit(self, event: HookEvent) -> None:
        """Emit a pipeline event, calling all registered callbacks.

        Callbacks are called in registration order. If a callback raises
        an exception, it is logged as a warning but does not stop other
        callbacks from running.

        Args:
            event: The event to emit.
        """
        callbacks = self._hooks.get(event.name, [])
        for callback in callbacks:
            try:
                callback(event)
            except Exception as exc:
                logger.warning(
                    "hook_callback_error",
                    event_name=event.name,
                    error=str(exc),
                )

    @property
    def registered_events(self) -> list[str]:
        """List of events that have at least one callback registered."""
        return sorted(name for name, cbs in self._hooks.items() if cbs)
