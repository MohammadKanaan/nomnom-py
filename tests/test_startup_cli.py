from pathlib import Path

from typer.testing import CliRunner

import nomnom.cli as cli_module
from nomnom.cli import app


class FakeInstaller:
    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = enabled
        self.enabled_config: Path | None = None
        self.disable_called = False

    def enable(self, config_path: Path) -> Path:
        self.enabled_config = config_path
        self.enabled = True
        return Path("/tmp/com.nomnom.watcher.plist")

    def disable(self) -> None:
        self.disable_called = True
        self.enabled = False

    def status(self) -> bool:
        return self.enabled


def test_startup_enable_uses_absolute_config_path(monkeypatch, tmp_path: Path) -> None:
    fake = FakeInstaller()
    config_path = tmp_path / "config.toml"
    config_path.write_text("[[watch]]\nname='inbox'\npaths=['./inbox']\n")
    monkeypatch.setattr(cli_module, "get_startup_installer", lambda: fake)

    runner = CliRunner()
    result = runner.invoke(app, ["startup", "enable", "--config", str(config_path)])

    assert result.exit_code == 0
    assert fake.enabled_config == config_path.resolve()
    assert "Startup launch enabled" in result.output


def test_startup_enable_fails_when_config_missing(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["startup", "enable", "--config", str(tmp_path / "missing.toml")],
    )

    assert result.exit_code == 1
    assert "Config file not found" in result.output


def test_startup_disable_calls_installer(monkeypatch) -> None:
    fake = FakeInstaller(enabled=True)
    monkeypatch.setattr(cli_module, "get_startup_installer", lambda: fake)

    runner = CliRunner()
    result = runner.invoke(app, ["startup", "disable"])

    assert result.exit_code == 0
    assert fake.disable_called is True
    assert "Startup launch disabled" in result.output


def test_startup_status_reports_enabled(monkeypatch) -> None:
    fake = FakeInstaller(enabled=True)
    monkeypatch.setattr(cli_module, "get_startup_installer", lambda: fake)

    runner = CliRunner()
    result = runner.invoke(app, ["startup", "status"])

    assert result.exit_code == 0
    assert "Startup launch is enabled" in result.output
