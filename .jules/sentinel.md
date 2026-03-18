## 2024-03-18 - Argument Injection in Plugin Install Command
**Vulnerability:** Argument injection via user-supplied plugin name in `subprocess.run(["uv", "pip", "install", ... package])`. Malicious users could input `-e` or `--index-url=...` which `uv pip` would interpret as flags.
**Learning:** Functions that wrap shell commands taking positional user input are vulnerable to flag injection if options are not explicitly separated from positional arguments.
**Prevention:** Always use the `--` flag when passing untrusted user input as positional arguments to command line tools (e.g. `uv pip install -- package`).
