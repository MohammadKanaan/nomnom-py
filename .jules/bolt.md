
## 2025-02-17 - Fast fnmatch caching for file filters
**Learning:** Caching string-pattern evaluations in high-frequency loops (like `fnmatch` against multiple patterns in file watchers) using `functools.lru_cache` provides significant performance boosts. However, caching only works natively if the arguments are immutable (like `tuple`). Converting list configurations natively to tuples upon reading configuration avoids repeated `tuple(list)` casting overhead during each lookup.
**Action:** Store immutable lists as tuples in dataclass configuration early on, then use `lru_cache` to aggressively cache filter functions mapping filenames and tuple patterns to boolean results to improve loop performance without sacrificing code readability.
