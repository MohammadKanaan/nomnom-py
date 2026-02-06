from typing import Protocol

from nomnom.effects import Effect
from nomnom.events import FileEvent


class Plugin(Protocol):
    def matches(self, event: FileEvent) -> bool: ...
    def handle(self, event: FileEvent) -> list[Effect]: ...
