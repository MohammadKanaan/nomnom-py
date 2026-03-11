## 2026-03-11 - Optimize event processing in nomnom-plugin-rules
**Learning:** In hot loops evaluating many rules against a single event, repeatedly accessing properties on data objects like `event.event_type.value`, `event.watch_group`, and `event.path.name` introduces measurable overhead in Python.
**Action:** Cache commonly accessed properties from objects before entering evaluation loops to minimize attribute access and method call overhead.
