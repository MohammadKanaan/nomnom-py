## 2024-05-15 - Cache Collections as Tuples

**Learning:** When using `@functools.lru_cache` to memoize functions evaluating collections (like matching file names against multiple patterns in a loop), we must pass the collections as immutable `tuple`s. Converting a `list` to a `tuple` repeatedly at the call site for the cache key negates the performance benefit in high-frequency loops.
**Action:** Store lists as immutable `tuple`s directly on the configuration or state objects (using `__post_init__` for dataclasses if needed to coerce incoming lists to tuples) to avoid repeated conversion overhead on cache lookups.
