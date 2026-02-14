from __future__ import annotations

import platform
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Callable, Protocol

LAUNCH_AGENT_LABEL = "com.nomnom.watcher"


class StartupInstaller(Protocol):
    def enable(self, config_path: Path) -> Path: ...

    def disable(self) -> None: ...

    def status(self) -> bool: ...


RunCommand = Callable[[list[str]], None]


def _run_subprocess(args: list[str]) -> None:
    subprocess.run(args, check=True)


class MacOSLaunchAgentInstaller:
    def __init__(
        self,
        *,
        home_dir: Path | None = None,
        run_command: RunCommand = _run_subprocess,
    ) -> None:
        self.home_dir = (home_dir or Path.home()).resolve()
        self.run_command = run_command
        self.launch_agents_dir = self.home_dir / "Library" / "LaunchAgents"
        self.logs_dir = self.home_dir / "Library" / "Logs" / "nomnom"
        self.plist_path = self.launch_agents_dir / f"{LAUNCH_AGENT_LABEL}.plist"

    def enable(self, config_path: Path) -> Path:
        resolved_config = config_path.resolve()
        self.launch_agents_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        plist_data = {
            "Label": LAUNCH_AGENT_LABEL,
            "ProgramArguments": [
                sys.executable,
                "-u",
                "-m",
                "nomnom.cli",
                "watch",
                "--config",
                str(resolved_config),
            ],
            "RunAtLoad": True,
            "KeepAlive": True,
            "WorkingDirectory": str(resolved_config.parent),
            "StandardOutPath": str(self.logs_dir / "watch.out.log"),
            "StandardErrorPath": str(self.logs_dir / "watch.err.log"),
        }

        self.plist_path.write_bytes(plistlib.dumps(plist_data))
        self.run_command(["launchctl", "load", "-w", str(self.plist_path)])
        return self.plist_path

    def disable(self) -> None:
        if not self.plist_path.exists():
            return

        self.run_command(["launchctl", "unload", "-w", str(self.plist_path)])
        self.plist_path.unlink()

    def status(self) -> bool:
        return self.plist_path.exists()


class LinuxStartupInstaller:
    def enable(self, config_path: Path) -> Path:
        raise NotImplementedError(
            "Linux startup integration is not implemented yet. "
            "Planned target: systemd user units."
        )

    def disable(self) -> None:
        raise NotImplementedError(
            "Linux startup integration is not implemented yet. "
            "Planned target: systemd user units."
        )

    def status(self) -> bool:
        raise NotImplementedError(
            "Linux startup integration is not implemented yet. "
            "Planned target: systemd user units."
        )


class WindowsStartupInstaller:
    def enable(self, config_path: Path) -> Path:
        raise NotImplementedError(
            "Windows startup integration is not implemented yet. "
            "Planned target: Task Scheduler or WinSW."
        )

    def disable(self) -> None:
        raise NotImplementedError(
            "Windows startup integration is not implemented yet. "
            "Planned target: Task Scheduler or WinSW."
        )

    def status(self) -> bool:
        raise NotImplementedError(
            "Windows startup integration is not implemented yet. "
            "Planned target: Task Scheduler or WinSW."
        )


def get_startup_installer(
    *,
    system_name: str | None = None,
    home_dir: Path | None = None,
    run_command: RunCommand = _run_subprocess,
) -> StartupInstaller:
    detected = system_name or platform.system()
    if detected == "Darwin":
        return MacOSLaunchAgentInstaller(home_dir=home_dir, run_command=run_command)
    if detected == "Linux":
        return LinuxStartupInstaller()
    if detected == "Windows":
        return WindowsStartupInstaller()
    raise NotImplementedError(f"Unsupported platform: {detected}")
