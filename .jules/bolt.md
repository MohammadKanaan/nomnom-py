## 2024-03-13 - Avoid redundant attribute access in plugin loops
**Learning:** In tight rule-evaluation loops processing many plugins (like `nomnom-plugin-rules`), repeatedly accessing attributes on complex objects like `FileEvent` (specifically Enum properties like `event_type.value` and Path properties like `path.name`) causes unnecessary overhead.
**Action:** Extract and cache primitive property values prior to the loop, then pass these cached values to evaluation methods to improve event processing throughput.
