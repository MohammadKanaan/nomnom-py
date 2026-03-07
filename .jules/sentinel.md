## 2023-10-27 - [Fix terminal output formatting injection]
**Vulnerability:** Unescaped user-controlled inputs (file paths, watch group names) were passed directly to `rich.console.print` in `nomnom/watcher.py`.
**Learning:** In applications using the `rich` library, unescaped strings containing brackets (like `[red]`) can cause `rich` to attempt markup evaluation. This can lead to local Denial of Service (MarkupError crashes) or unintended terminal formatting.
**Prevention:** Always use `escape()` from `rich.markup` when printing dynamically generated or untrusted strings (e.g. `escape(path.name)`) with `rich`.
