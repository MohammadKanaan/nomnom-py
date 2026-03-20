## 2025-02-28 - Prevent Argument Injection with Command Separator
**Vulnerability:** Argument injection when executing subcommands via `subprocess.run` (e.g., `uv pip install`) with user-provided input intended as a positional argument.
**Learning:** Even though `subprocess.run` with a list of arguments avoids shell injection, a malicious user can still inject arbitrary command-line options if the external program interprets positional strings starting with `-` or `--` as flags instead of data.
**Prevention:** Always use the `--` separator to explicitly delineate options from positional arguments, forcing the external command to treat subsequent inputs strictly as positional data (e.g., `["uv", "pip", "install", "--python", sys.executable, "--", package]`).
