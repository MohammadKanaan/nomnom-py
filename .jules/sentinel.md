## 2024-03-19 - Subprocess argument injection risk in plugin installation
**Vulnerability:** The command to install plugins using `subprocess.run` accepted a user-provided package name directly as a positional argument without explicit separator, allowing argument injection (e.g., `-e` options passed to pip install).
**Learning:** Even when running local tools like pip through `subprocess.run` with list arguments instead of shell strings, options or flags starting with `-` can be injected if passed as positional arguments.
**Prevention:** Always use the `--` separator to explicitly delineate options from positional arguments when executing subcommands with user-provided input.
