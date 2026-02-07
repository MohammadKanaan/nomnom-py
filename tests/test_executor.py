from pathlib import Path

import pytest

from nomnom.effects import CreateFile, DeleteFile, EditAction, EditFile, MoveFile
from nomnom.executor import execute


def test_execute_move_file(tmp_path: Path) -> None:
    source = tmp_path / "src.txt"
    source.write_text("hello")
    destination = tmp_path / "nested" / "dst.txt"

    execute(MoveFile(source=source, destination=destination))

    assert not source.exists()
    assert destination.read_text() == "hello"


def test_execute_delete_file(tmp_path: Path) -> None:
    path = tmp_path / "to-delete.txt"
    path.write_text("bye")

    execute(DeleteFile(path=path))

    assert not path.exists()


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


def test_execute_unknown_effect_raises_type_error() -> None:
    with pytest.raises(TypeError):
        execute("unexpected")
