## 2024-05-24 - Optimize tight loop event property access
**Learning:** In the `nomnom-plugin-rules` plugin, evaluating many rules in a loop causes significant redundant attribute access overhead on the `FileEvent` object properties (`event_type.value`, `watch_group`, and `path.name`).
**Action:** Extract and cache these properties before entering the rule evaluation loop, and pass the cached values to prevent redundant method calls and attribute lookups per rule.
