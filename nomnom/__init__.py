from importlib.metadata import PackageNotFoundError, version

from nomnom.effects import CreateFile, DeleteFile, EditAction, EditFile, Effect, EmitEvent, MoveFile
from nomnom.events import EventType, FileEvent
from nomnom.plugin import Plugin, SetupPlugin


def get_version() -> str:
    try:
        return version("nomnom")
    except PackageNotFoundError:
        return "dev"


__all__ = [
    "Plugin",
    "SetupPlugin",
    "FileEvent",
    "EventType",
    "Effect",
    "MoveFile",
    "DeleteFile",
    "CreateFile",
    "EditFile",
    "EmitEvent",
    "EditAction",
    "get_version",
]
