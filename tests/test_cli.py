from types import SimpleNamespace
import sys

from typer.testing import CliRunner

import nomnom.cli as cli_module
from nomnom.cli import app


def test_watch_prompts_setup_when_default_config_missing() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["watch"])

    assert result.exit_code == 1
    assert "Config file not found: config.toml" in result.output
    assert "Run `nomnom setup` to create one." in result.output


def test_plugin_install_runs_setup_for_new_plugin(
    monkeypatch,
) -> None:
    class PluginWithSetup:
        def __init__(self) -> None:
            self.setup_called = False

        def setup(self) -> None:
            self.setup_called = True

    plugin = PluginWithSetup()
    runner = CliRunner()
    seen_cmd = None

    def fake_run(cmd, *args, **kwargs):
        nonlocal seen_cmd
        seen_cmd = cmd
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        cli_module,
        "discover_new_plugins",
        lambda known_names: [("fresh", plugin)],
    )
    monkeypatch.setattr(
        "subprocess.run",
        fake_run,
    )

    result = runner.invoke(app, ["plugin-install", "nomnom-plugin-fresh"])

    assert result.exit_code == 0
    assert plugin.setup_called is True
    assert seen_cmd == [
        "uv",
        "pip",
        "install",
        "--python",
        sys.executable,
        "nomnom-plugin-fresh",
    ]
    assert "Running setup() for plugin 'fresh'..." in result.output
    assert "Setup completed for plugin 'fresh'." in result.output


def test_plugin_install_skips_setup_with_no_setup_flag(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        cli_module,
        "discover_new_plugins",
        lambda _: (_ for _ in ()).throw(AssertionError("discover_new_plugins called")),
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    result = runner.invoke(app, ["plugin-install", "nomnom-plugin-fresh", "--no-setup"])

    assert result.exit_code == 0
    assert "Skipping plugin setup (--no-setup)" in result.output


def test_plugin_install_handles_setup_failure(monkeypatch) -> None:
    class PluginWithFailingSetup:
        def setup(self) -> None:
            raise RuntimeError("boom")

    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        cli_module,
        "discover_new_plugins",
        lambda known_names: [("fresh", PluginWithFailingSetup())],
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    result = runner.invoke(app, ["plugin-install", "nomnom-plugin-fresh"])

    assert result.exit_code == 1
    assert "Setup failed for plugin 'fresh': boom" in result.output
    assert "One or more plugin setup steps failed." in result.output


def test_plugin_install_handles_keyboard_interrupt_during_setup(monkeypatch) -> None:
    class PluginWithInterruptedSetup:
        def setup(self) -> None:
            raise KeyboardInterrupt

    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        cli_module,
        "discover_new_plugins",
        lambda known_names: [("fresh", PluginWithInterruptedSetup())],
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    result = runner.invoke(app, ["plugin-install", "nomnom-plugin-fresh"])

    assert result.exit_code == 1
    assert "Setup cancelled for plugin 'fresh'." in result.output


def test_plugin_install_handles_no_new_plugins(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(cli_module, "discover_new_plugins", lambda known_names: [])
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    result = runner.invoke(app, ["plugin-install", "nomnom-plugin-fresh"])

    assert result.exit_code == 0
    assert "No new plugins detected after install; skipping setup." in result.output


def test_plugin_install_skips_plugin_without_setup(monkeypatch) -> None:
    class PluginWithoutSetup:
        def matches(self, event):
            return False

        def handle(self, event):
            return []

    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        cli_module,
        "discover_new_plugins",
        lambda known_names: [("fresh", PluginWithoutSetup())],
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    result = runner.invoke(app, ["plugin-install", "nomnom-plugin-fresh"])

    assert result.exit_code == 0
    assert "Plugin 'fresh' has no setup() method; skipping." in result.output
    assert "No plugin setup was executed." in result.output


def test_plugin_install_handles_missing_uv(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(cli_module, "get_installed_plugin_names", lambda: {"existing"})
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("uv")),
    )

    result = runner.invoke(app, ["plugin-install", "nomnom-plugin-fresh"])

    assert result.exit_code == 1
    assert "Installation failed: could not execute 'uv'" in result.output
