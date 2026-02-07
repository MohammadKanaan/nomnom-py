from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class EventType(Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass
class FileEvent:
    event_type: EventType
    path: Path
    watch_group: str
    created_at: datetime
