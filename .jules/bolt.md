## 2026-03-20 - Optimize File Change Coalescing
**Learning:** Checking file existence using `Path.exists()` is a costly I/O operation. Performing this check for every file in a watch batch significantly impacts performance, especially when most changes (modifications, single additions/deletions) do not require it.
**Action:** Always defer expensive I/O operations in loops to the most specific conditional blocks where they are strictly necessary.

## 2026-03-26 - Optimize Subpath Checking
**Learning:** Using try/except blocks with `Path.relative_to` for control flow adds significant overhead in hot loops.
**Action:** Use the faster `Path.is_relative_to()` boolean check instead of exception handling.
