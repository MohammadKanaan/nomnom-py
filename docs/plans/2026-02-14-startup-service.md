# Startup Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add startup-service management to nomnom with a production-ready macOS launchd implementation and clear extension points for Linux and Windows.

**Architecture:** Introduce a startup installer abstraction selected by platform. Implement the macOS installer as a LaunchAgent writer + `launchctl` integrator, and keep Linux/Windows as explicit placeholders so behavior is predictable and easy to extend.

**Tech Stack:** Python 3.11, Typer CLI, pytest

---

### Task 1: Startup installer abstraction

**Files:**
- Create: `nomnom/startup.py`
- Test: `tests/test_startup.py`

1. Define a `StartupInstaller` protocol with `enable`, `disable`, `status`.
2. Add a `get_startup_installer()` factory using `platform.system()`.
3. Add explicit Linux/Windows installer stubs that raise `NotImplementedError`.
4. Write tests that verify factory selection and stub behavior.

### Task 2: macOS LaunchAgent implementation

**Files:**
- Create: `nomnom/startup.py`
- Test: `tests/test_startup.py`

1. Add a `MacOSLaunchAgentInstaller` that writes `~/Library/LaunchAgents/com.nomnom.watcher.plist`.
2. Plist must include `ProgramArguments` with absolute `sys.executable` and `-m nomnom.cli watch --config <abs path>`.
3. Set `RunAtLoad=true`, `KeepAlive=true`, and log redirection in `~/Library/Logs/nomnom`.
4. Register/unregister with `launchctl` and verify via unit tests using subprocess stubs.

### Task 3: CLI integration

**Files:**
- Modify: `nomnom/cli.py`
- Modify: `nomnom/cli_commands.py`
- Modify: `tests/test_cli.py`

1. Add `nomnom startup enable`, `nomnom startup disable`, `nomnom startup status` commands.
2. `enable` takes `--config` and fails with clear message if config is missing.
3. Commands should use dependency-injected installer factory for testability.
4. Add CLI tests for success/failure and status output.

### Task 4: Verification and follow-up

**Files:**
- N/A

1. Run targeted tests for startup and CLI updates.
2. Run full test suite.
3. Document Linux/Windows follow-up as TODO comments in startup module.
