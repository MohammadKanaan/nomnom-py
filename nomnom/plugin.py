from typing import Protocol, runtime_checkable

from nomnom.effects import Effect
from nomnom.events import FileEvent


class Plugin(Protocol):
    def matches(self, event: FileEvent) -> bool: ...
    def handle(self, event: FileEvent) -> list[Effect]: ...


@runtime_checkable
class SetupPlugin(Plugin, Protocol):
    def setup(self) -> None: ...


def has_setup(plugin: Plugin) -> bool:
    return callable(getattr(plugin, "setup", None))


def run_plugin_setup(plugin: Plugin) -> None:
    setup_fn = getattr(plugin, "setup", None)
    if callable(setup_fn):
        setup_fn()
