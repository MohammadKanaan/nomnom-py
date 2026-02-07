from pathlib import Path

import pytest
import typer

import nomnom.create_plugin as create_plugin_module


def test_create_plugin_rejects_path_traversal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(create_plugin_module, "PLUGINS_DIR", tmp_path)

    with pytest.raises(typer.Exit) as exc_info:
        create_plugin_module.create_plugin("../../evil")

    assert exc_info.value.exit_code == 1
    assert not any(tmp_path.iterdir())


def test_create_plugin_creates_valid_structure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(create_plugin_module, "PLUGINS_DIR", tmp_path)

    create_plugin_module.create_plugin("valid_name")

    plugin_dir = tmp_path / "nomnom-plugin-valid-name"
    module_dir = plugin_dir / "nomnom_plugin_valid_name"
    pyproject_path = plugin_dir / "pyproject.toml"
    init_path = module_dir / "__init__.py"

    assert plugin_dir.is_dir()
    assert module_dir.is_dir()
    assert pyproject_path.is_file()
    assert init_path.is_file()

    pyproject_text = pyproject_path.read_text()
    assert 'valid-name = "nomnom_plugin_valid_name:ValidNamePlugin"' in pyproject_text


def test_create_plugin_rejects_existing_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(create_plugin_module, "PLUGINS_DIR", tmp_path)
    existing = tmp_path / "nomnom-plugin-transcribe"
    existing.mkdir(parents=True)

    with pytest.raises(typer.Exit) as exc_info:
        create_plugin_module.create_plugin("transcribe")

    assert exc_info.value.exit_code == 1


def test_create_plugin_generates_correct_class_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(create_plugin_module, "PLUGINS_DIR", tmp_path)

    create_plugin_module.create_plugin("pdf-parser")

    init_path = (
        tmp_path
        / "nomnom-plugin-pdf-parser"
        / "nomnom_plugin_pdf_parser"
        / "__init__.py"
    )
    init_text = init_path.read_text()

    assert "class PdfParserPlugin:" in init_text
