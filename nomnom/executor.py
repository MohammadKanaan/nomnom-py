import logging
import os
import shutil
import tempfile
from contextlib import suppress
from pathlib import Path

from nomnom.effects import CreateFile, DeleteFile, EditAction, EditFile, Effect, MoveFile

logger = logging.getLogger(__name__)
EFFECT_TEMPFILE_PREFIX = ".nomnom-tmp-"


def _default_file_mode() -> int:
    """Return the default file mode respecting the current umask."""
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


def _write_path_for(path: Path) -> Path:
    """Follow symlinks so rewrites update the referent instead of replacing the link."""
    return path.resolve(strict=False) if path.is_symlink() else path


def _write_bytes_atomically(
    path: Path,
    content: bytes,
    *,
    create_parent: bool,
) -> None:
    write_path = _write_path_for(path)
    if create_parent and not path.is_symlink():
        write_path.parent.mkdir(parents=True, exist_ok=True)

    mode = write_path.stat().st_mode if write_path.exists() else None
    with tempfile.NamedTemporaryFile(
        dir=write_path.parent,
        prefix=EFFECT_TEMPFILE_PREFIX,
        delete=False,
    ) as tmp:
        tmp.write(content)
        tmp_name = tmp.name

    try:
        os.chmod(tmp_name, mode if mode is not None else _default_file_mode())
        os.replace(tmp_name, write_path)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise


class EffectSkipped(Exception):
    """Raised when an effect is intentionally skipped (e.g. missing source/target)."""


def execute(effect: Effect) -> None:
    match effect:
        case MoveFile(source=src, destination=dst, overwrite=overwrite):
            if not src.exists():
                logger.warning(f"Move skipped; source missing: {src} -> {dst}")
                raise EffectSkipped(f"Move skipped; source missing: {src} -> {dst}")

            if dst.exists() and not overwrite:
                logger.warning(f"Move skipped; destination exists and overwrite=False: {dst}")
                raise EffectSkipped(f"Move skipped; destination exists and overwrite=False: {dst}")

            if dst.exists() and overwrite:
                logger.warning(f"Move overwriting existing file: {dst}")

            logger.info(f"Moving {src} -> {dst}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)

        case DeleteFile(path=path):
            try:
                path.unlink()
            except FileNotFoundError:
                logger.warning(f"Delete skipped; file missing: {path}")
                raise EffectSkipped(f"Delete skipped; file missing: {path}") from None
            logger.info(f"Deleting {path}")

        case CreateFile(path=path, content=content):
            logger.info(f"Creating {path}")
            _write_bytes_atomically(path, content, create_parent=True)

        case EditFile(path=path, action=action, content=content):
            logger.info(f"Editing {path} ({action.value})")
            existing = path.read_bytes() if path.exists() else b""
            new_content = content + existing if action is EditAction.PREPEND else existing + content
            _write_bytes_atomically(path, new_content, create_parent=False)

        case _:
            raise TypeError(f"Unhandled effect type: {type(effect).__name__}")
