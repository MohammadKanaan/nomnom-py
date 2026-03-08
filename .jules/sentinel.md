## 2025-02-14 - Argument Injection in Subprocess Run
**Vulnerability:** A package name provided by a user to the CLI tool could cause argument injection when passed to `subprocess.run` (e.g., passing `--help` or other options instead of a positional package argument).
**Learning:** Argument injection occurs when an untrusted string is used without `--` separator to signify the end of command-line options when passed to `subprocess.run` intended as a positional argument, leading to potential execution of unintended options.
**Prevention:** To prevent argument injection, always use the `--` separator to explicitly demarcate options from positional arguments when using `subprocess.run` with untrusted inputs intended as a positional argument.
