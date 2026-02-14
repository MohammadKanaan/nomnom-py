from pathlib import Path
import plistlib
import sys

import pytest

from nomnom import startup


def test_get_startup_installer_returns_macos_installer(tmp_path: Path) -> None:
    installer = startup.get_startup_installer(
        system_name="Darwin",
        home_dir=tmp_path,
        run_command=lambda _args: None,
    )

    assert isinstance(installer, startup.MacOSLaunchAgentInstaller)


@pytest.mark.parametrize("system_name", ["Linux", "Windows"])
def test_non_macos_installers_raise_not_implemented(system_name: str, tmp_path: Path) -> None:
    installer = startup.get_startup_installer(system_name=system_name)

    with pytest.raises(NotImplementedError):
        installer.enable(tmp_path / "config.toml")


def test_macos_enable_writes_plist_and_loads_launch_agent(tmp_path: Path) -> None:
    commands: list[list[str]] = []

    installer = startup.MacOSLaunchAgentInstaller(
        home_dir=tmp_path,
        run_command=lambda args: commands.append(args),
    )
    config_path = tmp_path / "config.toml"
    config_path.write_text("[[]]\n")

    plist_path = installer.enable(config_path)

    assert plist_path == tmp_path / "Library" / "LaunchAgents" / "com.nomnom.watcher.plist"
    assert plist_path.exists()

    plist_data = plistlib.loads(plist_path.read_bytes())
    assert plist_data["RunAtLoad"] is True
    assert plist_data["KeepAlive"] is True
    assert plist_data["ProgramArguments"] == [
        sys.executable,
        "-u",
        "-m",
        "nomnom.cli",
        "watch",
        "--config",
        str(config_path.resolve()),
    ]

    assert commands == [["launchctl", "load", "-w", str(plist_path)]]


def test_macos_disable_unloads_and_removes_plist(tmp_path: Path) -> None:
    commands: list[list[str]] = []

    installer = startup.MacOSLaunchAgentInstaller(
        home_dir=tmp_path,
        run_command=lambda args: commands.append(args),
    )
    config_path = tmp_path / "config.toml"
    config_path.write_text("[[]]\n")

    plist_path = installer.enable(config_path)
    commands.clear()

    installer.disable()

    assert commands == [["launchctl", "unload", "-w", str(plist_path)]]
    assert not plist_path.exists()


def test_macos_status_reflects_plist_presence(tmp_path: Path) -> None:
    installer = startup.MacOSLaunchAgentInstaller(
        home_dir=tmp_path,
        run_command=lambda _args: None,
    )
    config_path = tmp_path / "config.toml"
    config_path.write_text("[[]]\n")

    assert installer.status() is False
    installer.enable(config_path)
    assert installer.status() is True
