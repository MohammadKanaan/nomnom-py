## 2026-03-09 - Prevent Argument Injection in Subprocess Calls
**Vulnerability:** Argument injection when executing subcommands via `subprocess.run` (e.g., `uv pip install`). If a user provides an input intended as a positional argument (like a package name starting with `-`), it can be misinterpreted as an option flag.
**Learning:** This vulnerability existed because the `package` argument was appended directly to the command list without any separation, allowing users to potentially pass flags like `--index-url` or `--upgrade` maliciously.
**Prevention:** To prevent argument injection, always use the `--` separator to explicitly delineate options from positional arguments in `subprocess` commands where user input is included.
