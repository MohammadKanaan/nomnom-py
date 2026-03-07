## 2024-05-18 - Caching Property Accesses Before Loops
**Learning:** In hot loops such as rule evaluation during file events (`RulesPlugin.matches` and `RulesPlugin.handle`), repeated attribute accesses (`event.event_type.value`, `event.path.name`, etc.) incur overhead.
**Action:** Extract and cache necessary properties into local variables before entering loops.
