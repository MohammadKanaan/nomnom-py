## 2024-05-24 - Optimize rule evaluation by caching event properties
**Learning:** In the `nomnom-plugin-rules` plugin, rule evaluation iterating over multiple events incurs noticeable overhead because it redundantly accesses nested properties like `event_type.value` and `path.name` within the iteration.
**Action:** Extract and cache `FileEvent` properties before rule-evaluation loops to avoid repetitive attribute access and method call overhead. This keeps tight evaluation loops fast and efficient.
