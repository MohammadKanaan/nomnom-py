from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nomnom.events import FileEvent


class EditAction(Enum):
    PREPEND = "prepend"
    APPEND = "append"


@dataclass
class MoveFile:
    source: Path
    destination: Path


@dataclass
class DeleteFile:
    path: Path


@dataclass
class CreateFile:
    path: Path
    content: bytes


@dataclass
class EditFile:
    path: Path
    action: EditAction
    content: bytes


@dataclass
class EmitEvent:
    event: FileEvent


Effect = MoveFile | DeleteFile | CreateFile | EditFile | EmitEvent
