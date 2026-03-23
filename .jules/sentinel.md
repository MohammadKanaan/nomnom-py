## 2024-05-24 - Prevent Argument Injection and Markup Injection
**Vulnerability:** Argument injection when installing plugins via CLI and markup injection (Denial of Service) when displaying file events.
**Learning:** `subprocess.run` with untrusted input at the end of the argument list can lead to argument injection if the input starts with `-` or `--`. Also, when using Rich to format terminal output, untrusted strings (like filenames) must be escaped, or they can trigger `MarkupError`s and crash the application.
**Prevention:** Always use the `--` separator before positional arguments in `subprocess.run` to explicitly mark the end of options. Always use `rich.markup.escape()` to sanitize untrusted strings before printing them with `rich.console`.

## 2024-05-18 - Argument Injection in plugin_remove_command
**Vulnerability:** The `plugin_remove_command` in `nomnom/cli_commands.py` executed `uv pip uninstall` without properly escaping user-provided input, allowing argument injection (e.g. passing `--break-system-packages` or other arguments).
**Learning:** Argument injection can happen even when using list-based `subprocess.run` arguments if the external tool has positional options preceded by `-` or `--`.
**Prevention:** Always use `--` separator in CLI tools when evaluating user input as positional arguments, to tell the parser that subsequent items should not be treated as options.
