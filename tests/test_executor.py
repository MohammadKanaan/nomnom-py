import os
from pathlib import Path

import pytest

from nomnom.effects import CreateFile, DeleteFile, EditAction, EditFile, MoveFile
from nomnom.executor import execute, EffectSkipped


def test_execute_move_file(tmp_path: Path) -> None:
    source = tmp_path / "src.txt"
    source.write_text("hello")
    destination = tmp_path / "nested" / "dst.txt"

    execute(MoveFile(source=source, destination=destination))

    assert not source.exists()
    assert destination.read_text() == "hello"


def test_execute_move_file_missing_source_is_noop(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source = tmp_path / "missing.txt"
    destination = tmp_path / "nested" / "dst.txt"
    caplog.set_level("WARNING")

    with pytest.raises(EffectSkipped):
        execute(MoveFile(source=source, destination=destination))

    assert not destination.exists()
    assert "Move skipped; source missing" in caplog.text


def test_execute_move_file_overwrites_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source = tmp_path / "src.txt"
    source.write_text("new")
    destination = tmp_path / "dst.txt"
    destination.write_text("old")
    caplog.set_level("WARNING")

    execute(MoveFile(source=source, destination=destination, overwrite=True))

    assert destination.read_text() == "new"
    assert "overwriting" in caplog.text


def test_execute_delete_file(tmp_path: Path) -> None:
    path = tmp_path / "to-delete.txt"
    path.write_text("bye")

    execute(DeleteFile(path=path))

    assert not path.exists()


def test_execute_delete_file_missing_is_skipped(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = tmp_path / "nonexistent.txt"
    caplog.set_level("WARNING")

    with pytest.raises(EffectSkipped):
        execute(DeleteFile(path=path))

    assert "Delete skipped; file missing" in caplog.text


def test_execute_create_file(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "new.txt"

    execute(CreateFile(path=path, content=b"created"))

    assert path.read_bytes() == b"created"


def test_execute_edit_file_prepend(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_bytes(b"world")

    execute(EditFile(path=path, action=EditAction.PREPEND, content=b"hello "))

    assert path.read_bytes() == b"hello world"


def test_execute_edit_file_append(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_bytes(b"hello")

    execute(EditFile(path=path, action=EditAction.APPEND, content=b" world"))

    assert path.read_bytes() == b"hello world"


def test_execute_edit_file_nonexistent_creates(tmp_path: Path) -> None:
    path = tmp_path / "missing.txt"

    execute(EditFile(path=path, action=EditAction.APPEND, content=b"new"))

    assert path.read_bytes() == b"new"


def test_execute_edit_file_prepend_nonexistent(tmp_path: Path) -> None:
    path = tmp_path / "missing.txt"

    execute(EditFile(path=path, action=EditAction.PREPEND, content=b"new"))

    assert path.read_bytes() == b"new"


def test_execute_edit_file_prepend_multiline(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_bytes(b"line 2\nline 3")

    execute(EditFile(path=path, action=EditAction.PREPEND, content=b"line 1\n"))

    assert path.read_bytes() == b"line 1\nline 2\nline 3"


def test_execute_edit_file_prepend_empty_content(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_bytes(b"existing")

    execute(EditFile(path=path, action=EditAction.PREPEND, content=b""))

    assert path.read_bytes() == b"existing"


def test_execute_create_file_atomic(tmp_path: Path) -> None:
    path = tmp_path / "atomic.txt"

    execute(CreateFile(path=path, content=b"atomic content"))

    assert path.read_bytes() == b"atomic content"
    # No leftover temp files
    assert len(list(tmp_path.iterdir())) == 1


def test_execute_edit_file_atomic(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_bytes(b"original")

    execute(EditFile(path=path, action=EditAction.APPEND, content=b" appended"))

    assert path.read_bytes() == b"original appended"
    # No leftover temp files
    assert len(list(tmp_path.iterdir())) == 1


def test_execute_create_file_preserves_existing_permissions(tmp_path: Path) -> None:
    path = tmp_path / "existing.txt"
    path.write_bytes(b"old")
    os.chmod(path, 0o755)

    execute(CreateFile(path=path, content=b"new"))

    assert path.read_bytes() == b"new"
    assert path.stat().st_mode & 0o777 == 0o755


def test_execute_create_file_new_file_respects_umask(tmp_path: Path) -> None:
    path = tmp_path / "brand_new.txt"

    execute(CreateFile(path=path, content=b"content"))

    # Should not be 0o600 (the NamedTemporaryFile default)
    mode = path.stat().st_mode & 0o777
    assert mode != 0o600


def test_execute_edit_file_preserves_permissions(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_bytes(b"hello")
    os.chmod(path, 0o755)

    execute(EditFile(path=path, action=EditAction.APPEND, content=b" world"))

    assert path.read_bytes() == b"hello world"
    assert path.stat().st_mode & 0o777 == 0o755


def test_execute_unknown_effect_raises_type_error() -> None:
    with pytest.raises(TypeError):
        execute("unexpected")
