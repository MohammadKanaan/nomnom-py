import logging
import shutil

from nomnom.effects import CreateFile, DeleteFile, EditAction, EditFile, Effect, MoveFile

logger = logging.getLogger(__name__)


class EffectSkipped(Exception):
    """Raised when an effect is intentionally skipped (e.g. missing source/target)."""


def execute(effect: Effect) -> None:
    match effect:
        case MoveFile(source=src, destination=dst, overwrite=overwrite):
            if not src.exists():
                logger.warning(f"Move skipped; source missing: {src} -> {dst}")
                raise EffectSkipped(f"Move skipped; source missing: {src} -> {dst}")

            if dst.exists() and overwrite:
                logger.warning(f"Move overwriting existing file: {dst}")

            logger.info(f"Moving {src} -> {dst}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)

        case DeleteFile(path=path):
            if not path.exists():
                logger.warning(f"Delete skipped; file missing: {path}")
                raise EffectSkipped(f"Delete skipped; file missing: {path}")
            logger.info(f"Deleting {path}")
            path.unlink()

        case CreateFile(path=path, content=content):
            logger.info(f"Creating {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        case EditFile(path=path, action=action, content=content):
            logger.info(f"Editing {path} ({action.value})")
            existing = path.read_bytes() if path.exists() else b""
            if action is EditAction.PREPEND:
                path.write_bytes(content + existing)
            else:
                path.write_bytes(existing + content)

        case _:
            raise TypeError(f"Unhandled effect type: {type(effect).__name__}")
