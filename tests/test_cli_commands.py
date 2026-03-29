from nomnom.commands.plugin import _warn_missing_config


def test_warn_missing_config_warning(capsys, tmp_path):
    config_path = tmp_path / "missing.toml"
    _warn_missing_config(config_path)
    captured = capsys.readouterr()
    assert "Warning: Configuration file" in captured.out
    assert "not found" in captured.out
    assert "Run 'nomnom setup' to create one" in captured.out

def test_warn_missing_config_error(capsys, tmp_path):
    config_path = tmp_path / "missing.toml"
    _warn_missing_config(config_path, is_error=True)
    captured = capsys.readouterr()
    assert "Error: Configuration file" in captured.out
    assert "not found" in captured.out
    assert "Run 'nomnom setup' to create one" not in captured.out

def test_warn_missing_config_exists(capsys, tmp_path):
    config_path = tmp_path / "exists.toml"
    config_path.write_text("content")
    _warn_missing_config(config_path)
    captured = capsys.readouterr()
    assert captured.out == ""
