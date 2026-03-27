import logging
import shutil

from nomnom.effects import CreateFile, DeleteFile, EditAction, EditFile, Effect, MoveFile

logger = logging.getLogger(__name__)


def execute(effect: Effect) -> bool:
    match effect:
        case MoveFile(source=src, destination=dst):
            if not src.exists():
                logger.warning(f"Move skipped; source missing: {src} -> {dst}")
                return False

            logger.info(f"Moving {src} -> {dst}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
            return True

        case DeleteFile(path=path):
            logger.info(f"Deleting {path}")
            path.unlink()
            return True

        case CreateFile(path=path, content=content):
            logger.info(f"Creating {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            return True

        case EditFile(path=path, action=action, content=content):
            logger.info(f"Editing {path} ({action.value})")
            if action is EditAction.PREPEND:
                existing = path.read_bytes() if path.exists() else b""
                path.write_bytes(content + existing)
            else:
                # O(1) performance optimization: use binary append mode
                # instead of reading the entire file into memory (O(N))
                with path.open("ab") as f:
                    f.write(content)
            return True

        case _:
            raise TypeError(f"Unhandled effect type: {type(effect).__name__}")
