from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nomnom import executor
from nomnom.effects import EmitEvent
from nomnom.events import FileEvent
from nomnom.executor import EffectSkipped
from nomnom.plugin import Plugin

if TYPE_CHECKING:
    from nomnom.stats import WatchStats

logger = logging.getLogger(__name__)

DEFAULT_MAX_DEPTH = 10


def dispatch(
    event: FileEvent,
    plugins: list[tuple[str, Plugin]],
    *,
    stats: WatchStats | None = None,
    depth: int = 0,
    max_depth: int = DEFAULT_MAX_DEPTH,
    dry_run: bool = False,
) -> None:
    if depth >= max_depth:
        logger.warning(
            f"Max event depth ({max_depth}) reached, dropping event: "
            f"{event.event_type.value} {event.path}"
        )
        return

    if stats is not None:
        stats.record_event()

    for name, plugin in plugins:
        try:
            if not plugin.matches(event):
                continue
        except Exception:
            logger.exception(f"Plugin '{name}' crashed in matches()")
            continue

        logger.info(f"Plugin '{name}' matched {event.path}")
        if stats is not None:
            stats.record_match(name)

        try:
            effects = plugin.handle(event)
        except Exception:
            logger.exception(f"Plugin '{name}' crashed in handle()")
            continue

        for effect in effects:
            if isinstance(effect, EmitEvent):
                dispatch(
                    effect.event,
                    plugins,
                    stats=stats,
                    depth=depth + 1,
                    max_depth=max_depth,
                    dry_run=dry_run,
                )
            else:
                if dry_run:
                    logger.info(
                        f"[DRY RUN] Would execute {type(effect).__name__}: {effect}"
                    )
                    if stats is not None:
                        stats.record_dry_run_effect()
                    continue

                try:
                    executor.execute(effect)
                    if stats is not None:
                        stats.record_effect()
                except EffectSkipped:
                    pass
                except Exception:
                    logger.exception(
                        f"Effect {type(effect).__name__} failed (from plugin '{name}')"
                    )
