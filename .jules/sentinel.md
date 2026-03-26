## 2024-05-24 - Prevent Argument Injection and Markup Injection
**Vulnerability:** Argument injection when installing plugins via CLI and markup injection (Denial of Service) when displaying file events.
**Learning:** `subprocess.run` with untrusted input at the end of the argument list can lead to argument injection if the input starts with `-` or `--`. Also, when using Rich to format terminal output, untrusted strings (like filenames) must be escaped, or they can trigger `MarkupError`s and crash the application.
**Prevention:** Always use the `--` separator before positional arguments in `subprocess.run` to explicitly mark the end of options. Always use `rich.markup.escape()` to sanitize untrusted strings before printing them with `rich.console`.

## 2025-03-26 - Extended Protection against Argument Injection and Markup Injection
**Vulnerability:** Argument injection during plugin removal and markup injection (Denial of Service) when displaying plugin stats and configuration lists.
**Learning:** The `--` separator must be universally applied across all `subprocess.run` calls involving untrusted inputs (e.g., `uninstall_cmd`). Furthermore, `rich.markup.escape()` must be used consistently across all terminal outputs rendering untrusted configuration or paths (like tables in `stats.py` and `cli_commands.py`).
**Prevention:** Always use `--` in `subprocess.run` to terminate options. Always sanitize dynamic configuration keys and paths using `escape()` before `Table.add_row` or `Console.print`.
