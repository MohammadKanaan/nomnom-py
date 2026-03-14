## 2025-02-28 - [Argument Injection in uv pip install]
**Vulnerability:** The `uv pip install` command executed via `subprocess.run` with a user-provided `package` string is vulnerable to argument injection, where options starting with `-` could be passed instead of positional arguments.
**Learning:** This could allow attackers to pass arbitrary flags to `uv pip install`, leading to unintended behavior or arbitrary file writes.
**Prevention:** Use the `--` separator to explicitly delineate options from positional arguments when passing user input to `subprocess.run`.
