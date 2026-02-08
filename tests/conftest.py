from datetime import datetime
from pathlib import Path

import pytest

from nomnom.events import EventType, FileEvent


@pytest.fixture
def make_event():
    def _make(
        event_type: EventType = EventType.CREATED,
        path: Path = Path("/tmp/test.txt"),
        watch_group: str = "inbox",
    ) -> FileEvent:
        return FileEvent(
            event_type=event_type,
            path=path,
            watch_group=watch_group,
            created_at=datetime.now(),
        )

    return _make


class StubPlugin:
    def __init__(self, matches_result: bool = True, effects: list | None = None):
        self.matches_result = matches_result
        self.effects = effects or []
        self.matched_events: list[FileEvent] = []
        self.handled_events: list[FileEvent] = []

    def matches(self, event: FileEvent) -> bool:
        self.matched_events.append(event)
        return self.matches_result

    def handle(self, event: FileEvent) -> list:
        self.handled_events.append(event)
        return self.effects


@pytest.fixture
def stub_plugin_cls():
    return StubPlugin
