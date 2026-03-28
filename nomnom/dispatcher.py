from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING

from nomnom import executor
from nomnom.effects import EmitEvent
from nomnom.events import FileEvent
from nomnom.executor import EffectSkipped
from nomnom.plugin import PluginEntry

if TYPE_CHECKING:
    from nomnom.stats import WatchStats

logger = logging.getLogger(__name__)

DEFAULT_MAX_DEPTH = 10


def dispatch(
    event: FileEvent,
    plugins: list[PluginEntry],
    *,
    stats: WatchStats,
    max_depth: int = DEFAULT_MAX_DEPTH,
    dry_run: bool = False,
) -> None:
    stack: deque[tuple[FileEvent, int]] = deque()
    stack.append((event, 0))

    while stack:
        current_event, depth = stack.pop()

        if depth >= max_depth:
            logger.warning(
                f"Max event depth ({max_depth}) reached, dropping event: "
                f"{current_event.event_type.value} {current_event.path}"
            )
            continue

        stats.record_event()

        emitted: list[FileEvent] = []

        for name, plugin in plugins:
            try:
                if not plugin.matches(current_event):
                    continue
            except Exception:
                logger.exception(f"Plugin '{name}' crashed in matches()")
                continue

            logger.info(f"Plugin '{name}' matched {current_event.path}")
            stats.record_match(name)

            try:
                effects = plugin.handle(current_event)
            except Exception:
                logger.exception(f"Plugin '{name}' crashed in handle()")
                continue

            for effect in effects:
                if isinstance(effect, EmitEvent):
                    emitted.append(effect.event)
                else:
                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would execute {type(effect).__name__}: {effect}"
                        )
                        stats.record_dry_run_effect()
                        continue

                    try:
                        executor.execute(effect)
                        stats.record_effect()
                    except EffectSkipped:
                        pass
                    except Exception:
                        logger.exception(
                            f"Effect {type(effect).__name__} failed (from plugin '{name}')"
                        )

        # Push in reverse so first-emitted is popped first (DFS left-to-right order)
        # TODO: add tests for multi-plugin emit interleaving order
        for emitted_event in reversed(emitted):
            stack.append((emitted_event, depth + 1))
