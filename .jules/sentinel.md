## 2024-05-24 - Prevent Argument Injection and Markup Injection
**Vulnerability:** Argument injection when installing plugins via CLI and markup injection (Denial of Service) when displaying file events.
**Learning:** `subprocess.run` with untrusted input at the end of the argument list can lead to argument injection if the input starts with `-` or `--`. Also, when using Rich to format terminal output, untrusted strings (like filenames) must be escaped, or they can trigger `MarkupError`s and crash the application.
**Prevention:** Always use the `--` separator before positional arguments in `subprocess.run` to explicitly mark the end of options. Always use `rich.markup.escape()` to sanitize untrusted strings before printing them with `rich.console`.

## 2026-03-24 - Prevent Argument Injection in Subprocess Run
**Vulnerability:** Argument injection when removing plugins via CLI.
**Learning:** `subprocess.run` with untrusted input at the end of the argument list can lead to argument injection if the input starts with `-` or `--`. The `plugin_remove_command` was vulnerable when calling `uv pip uninstall`.
**Prevention:** Always use the `--` separator before positional arguments in `subprocess.run` to explicitly mark the end of options.
