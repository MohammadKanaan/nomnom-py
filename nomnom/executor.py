import logging
import os
import shutil
import tempfile
from pathlib import Path

from nomnom.effects import CreateFile, DeleteFile, EditAction, EditFile, Effect, MoveFile

logger = logging.getLogger(__name__)

def _default_file_mode() -> int:
    """Return the default file mode respecting the current umask."""
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


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
            mode = path.stat().st_mode if path.exists() else None
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
                tmp.write(content)
                tmp_name = tmp.name
            try:
                os.chmod(tmp_name, mode if mode is not None else _default_file_mode())
                os.replace(tmp_name, path)
            except BaseException:
                os.unlink(tmp_name)
                raise

        case EditFile(path=path, action=action, content=content):
            logger.info(f"Editing {path} ({action.value})")
            mode = path.stat().st_mode if path.exists() else None
            existing = path.read_bytes() if path.exists() else b""
            new_content = content + existing if action is EditAction.PREPEND else existing + content
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
                tmp.write(new_content)
                tmp_name = tmp.name
            try:
                os.chmod(tmp_name, mode if mode is not None else _default_file_mode())
                os.replace(tmp_name, path)
            except BaseException:
                os.unlink(tmp_name)
                raise

        case _:
            raise TypeError(f"Unhandled effect type: {type(effect).__name__}")
