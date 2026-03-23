from pathlib import Path

import pytest

from nomnom.validation import validate_module_path_containment, validate_plugin_name


@pytest.mark.parametrize(
    "name,expected",
    [
        ("transcribe", "transcribe"),
        ("pdf-parser", "pdf-parser"),
        ("my_plugin", "my-plugin"),
        ("  My_Plugin  ", "my-plugin"),
    ],
)
def test_validate_plugin_name_valid(name: str, expected: str) -> None:
    assert validate_plugin_name(name) == expected


@pytest.mark.parametrize(
    "name",
    [
        "../evil",
        "/tmp/evil",
        "foo/bar",
        r"foo\\bar",
        "plugin@123",
        "",
        "~/.hidden",
    ],
)
def test_validate_plugin_name_invalid(name: str) -> None:
    with pytest.raises(ValueError):
        validate_plugin_name(name)


def test_validate_module_path_containment_file(tmp_path: Path) -> None:
    plugin_root = tmp_path / "nomnom-plugin-safe"
    plugin_root.mkdir()
    module_file = plugin_root / "nomnom_plugin_safe.py"
    module_file.write_text("class SafePlugin:\n    pass\n")

    result = validate_module_path_containment(plugin_root, "nomnom_plugin_safe")

    assert result == module_file.resolve()


def test_validate_module_path_containment_package(tmp_path: Path) -> None:
    plugin_root = tmp_path / "nomnom-plugin-safe"
    module_dir = plugin_root / "nomnom_plugin_safe"
    module_dir.mkdir(parents=True)
    init_file = module_dir / "__init__.py"
    init_file.write_text("class SafePlugin:\n    pass\n")

    result = validate_module_path_containment(plugin_root, "nomnom_plugin_safe")

    assert result == init_file.resolve()


@pytest.mark.parametrize(
    "module_path",
    [
        "/tmp/malicious",
        "~/.bad.module",
        "C:\\temp\\malicious",
        "..evil",
        "evil..module",
        "evil.",
        ".evil",
        "",
        "evil:Thing",
    ],
)
def test_validate_module_path_containment_rejects_unsafe(tmp_path: Path, module_path: str) -> None:
    plugin_root = tmp_path / "nomnom-plugin-safe"
    plugin_root.mkdir()

    assert validate_module_path_containment(plugin_root, module_path) is None


def test_validate_module_path_containment_rejects_symlink_escape(tmp_path: Path) -> None:
    plugin_root = tmp_path / "nomnom-plugin-safe"
    plugin_root.mkdir()

    outside = tmp_path / "outside.py"
    outside.write_text("class Evil:\n    pass\n")

    link = plugin_root / "nomnom_plugin_safe.py"
    link.symlink_to(outside)

    assert validate_module_path_containment(plugin_root, "nomnom_plugin_safe") is None
