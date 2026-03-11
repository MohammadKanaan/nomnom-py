import timeit
import re
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from datetime import datetime

class EventType(Enum):
    CREATED = "created"

@dataclass
class FileEvent:
    event_type: EventType
    path: Path
    watch_group: str
    created_at: datetime

@dataclass
class Rule:
    on: str
    match: re.Pattern
    watch_group: str

    def matches(self, event: FileEvent) -> bool:
        if event.event_type.value != self.on:
            return False
        if self.watch_group is not None and self.watch_group != event.watch_group:
            return False
        return bool(self.match.search(event.path.name))

    def matches_attrs(self, event_type_val: str, watch_group: str, path_name: str) -> bool:
        if event_type_val != self.on:
            return False
        if self.watch_group is not None and self.watch_group != watch_group:
            return False
        return bool(self.match.search(path_name))

rules = [Rule("created", re.compile(f"file_{i}"), "group1") for i in range(100)]
event = FileEvent(EventType.CREATED, Path("/tmp/file_99.txt"), "group1", datetime.now())

def test_original():
    return any(rule.matches(event) for rule in rules)

def test_optimized():
    event_type_val = event.event_type.value
    watch_group = event.watch_group
    path_name = event.path.name
    return any(rule.matches_attrs(event_type_val, watch_group, path_name) for rule in rules)

print("Original:", timeit.timeit(test_original, number=10000))
print("Optimized:", timeit.timeit(test_optimized, number=10000))
