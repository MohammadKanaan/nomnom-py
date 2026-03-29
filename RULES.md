# Rules Plugin

`nomnom` ships with a built-in `rules` plugin for simple file automation.

Define file-event rules in `rules.toml` next to your active `config.toml`.
`nomnom` scans those two files together: by default it reads both from the current project directory, and if you pass `--config /path/to/config.toml` it will read `/path/to/rules.toml`.

## Rule Format

Use `[[rule]]` blocks:

```toml
[[rule]]
name = "archive pdfs"
on = "created"          # created | modified | deleted
match = "\\.pdf$"       # regex matched against filename only
watch_group = "inbox"   # optional
action = "move"         # prepend | append | delete | move
destination = "./archive/"  # required for move
content = "..."             # required for prepend/append
```

## Rules

- Rules are evaluated top-to-bottom.
- A file can match multiple rules; matching rules all run in file order.
- `match` checks `event.path.name` (not full path).
- Regex flavor is Python `re` syntax.
- Matching is case-sensitive by default. Use inline flags (for example `(?i)`) for case-insensitive patterns.
- `watch_group` is optional; if omitted, the rule applies to all groups.
- If `move` destination ends with `/` or points to an existing directory, filename is preserved.
- Otherwise destination is treated as an explicit target file path.
- `move` does not infer missing directories from names like `./archive` (no trailing slash). Use `./archive/` to preserve filename.
- Extra fields are ignored unless required by the action.
- `content` on a `move` rule is ignored.

## Execution Notes

- All matching rules for one event are evaluated against the same original event path.
- Effects run in rule order. If an earlier rule moves a file, later effects that use the old path may fail at execution time.
- This plugin does not emit recursive events itself.
- Filesystem effects can still produce new watcher events if affected paths are watched.

## Watch Groups

- `watch_group` names come from `config.toml` `[[watch]]` entries.
- A file is assigned to the most specific watched root path that contains it.

## Error Handling

- Missing `rules.toml`: plugin starts with no rules and logs an info message.
- Invalid TOML syntax: plugin starts with no rules and logs a warning.
- Invalid rules handling: Invalid rules are skipped and a warning is logged; other rules still load.

## File Placement

- Keep `config.toml` and `rules.toml` in the same directory.
- Relative paths inside `config.toml` are resolved from the config file's directory.
- The built-in `rules` plugin reads the colocated `rules.toml` from that same directory.
