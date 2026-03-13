from __future__ import annotations

import logging
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nomnom.effects import DeleteFile, EditAction, EditFile, Effect, MoveFile
from nomnom.events import FileEvent

logger = logging.getLogger(__name__)

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = PLUGIN_ROOT / "rules.toml"

VALID_EVENTS = {"created", "modified", "deleted"}
VALID_ACTIONS = {"prepend", "append", "delete", "move"}


@dataclass(frozen=True)
class Rule:
    name: str
    on: str
    match: re.Pattern[str]
    action: str
    content: str | None = None
    destination: str | None = None
    watch_group: str | None = None

    def matches(self, event_type_value: str, watch_group: str, path_name: str) -> bool:
        if event_type_value != self.on:
            return False
        if self.watch_group is not None and self.watch_group != watch_group:
            return False
        return bool(self.match.search(path_name))


class RulesPlugin:
    def __init__(self) -> None:
        self._rules = self._load_rules()

    def matches(self, event: FileEvent) -> bool:
        # Cache properties to avoid redundant attribute access overhead in the loop
        event_type_value = event.event_type.value
        watch_group = event.watch_group
        path_name = event.path.name
        return any(rule.matches(event_type_value, watch_group, path_name) for rule in self._rules)

    def handle(self, event: FileEvent) -> list[Effect]:
        effects: list[Effect] = []

        # Cache properties to avoid redundant attribute access overhead in the loop
        event_type_value = event.event_type.value
        watch_group = event.watch_group
        path_name = event.path.name

        for rule in self._rules:
            if not rule.matches(event_type_value, watch_group, path_name):
                continue

            if rule.action == "prepend":
                effects.append(
                    EditFile(
                        path=event.path,
                        action=EditAction.PREPEND,
                        content=(rule.content or "").encode(),
                    )
                )
            elif rule.action == "append":
                effects.append(
                    EditFile(
                        path=event.path,
                        action=EditAction.APPEND,
                        content=(rule.content or "").encode(),
                    )
                )
            elif rule.action == "delete":
                effects.append(DeleteFile(path=event.path))
            elif rule.action == "move":
                effects.append(
                    MoveFile(
                        source=event.path,
                        destination=_resolve_destination(
                            destination=rule.destination or "",
                            source_name=path_name,
                        ),
                    )
                )

        return effects

    def _load_rules(self) -> list[Rule]:
        if not RULES_PATH.is_file():
            logger.info("Rules file not found at %s", RULES_PATH)
            return []

        try:
            raw = tomllib.loads(RULES_PATH.read_text())
        except Exception as exc:
            logger.warning("Failed to parse rules file at %s: %s", RULES_PATH, exc)
            return []

        items = raw.get("rule")
        if not isinstance(items, list):
            logger.warning("Skipping invalid rules payload: expected [[rule]] list")
            return []

        rules: list[Rule] = []
        for candidate in items:
            rule = _parse_rule(candidate)
            if rule is None:
                logger.warning("Skipping invalid rule: %r", candidate)
                continue
            rules.append(rule)

        logger.info(
            "Loaded %d rule(s) from %s. Restart nomnom to pick up changes.",
            len(rules),
            RULES_PATH,
        )
        return rules


def _parse_rule(candidate: Any) -> Rule | None:
    if not isinstance(candidate, dict):
        return None

    name = candidate.get("name")
    on = candidate.get("on")
    match = candidate.get("match")
    action = candidate.get("action")
    watch_group = candidate.get("watch_group")
    content = candidate.get("content")
    destination = candidate.get("destination")

    if not isinstance(name, str) or not name.strip():
        return None
    if not isinstance(on, str) or on not in VALID_EVENTS:
        return None
    if not isinstance(match, str):
        return None
    if not isinstance(action, str) or action not in VALID_ACTIONS:
        return None
    if watch_group is not None and not isinstance(watch_group, str):
        return None

    if action in {"prepend", "append"} and not isinstance(content, str):
        return None
    if action == "move" and (
        not isinstance(destination, str) or not destination.strip()
    ):
        return None

    try:
        pattern = re.compile(match)
    except re.error:
        return None

    return Rule(
        name=name,
        on=on,
        match=pattern,
        action=action,
        content=content if isinstance(content, str) else None,
        destination=destination if isinstance(destination, str) else None,
        watch_group=watch_group if isinstance(watch_group, str) else None,
    )


def _resolve_destination(*, destination: str, source_name: str) -> Path:
    dest_path = Path(destination)
    if destination.endswith(("/", "\\")) or (dest_path.exists() and dest_path.is_dir()):
        return dest_path / source_name
    return dest_path
