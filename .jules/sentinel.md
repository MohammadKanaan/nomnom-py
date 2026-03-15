## 2024-03-15 - [Argument Injection in plugin install]
**Vulnerability:** Argument injection via a malicious plugin name (e.g., `-h` or another option) because `subprocess.run` executes `uv pip install <package>` directly, allowing user input to be parsed as options by `pip`.
**Learning:** `uv pip install` enforces packages provided after `--` must start with an alphanumeric character. However, even without this restriction, using `--` to separate positional arguments from options prevents parameter injection.
**Prevention:** Always use `--` to cleanly separate command options from user-supplied positional arguments when executing shell commands or invoking subprocesses like `uv`.
