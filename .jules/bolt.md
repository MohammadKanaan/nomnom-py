## 2026-03-20 - Optimize File Change Coalescing
**Learning:** Checking file existence using `Path.exists()` is a costly I/O operation. Performing this check for every file in a watch batch significantly impacts performance, especially when most changes (modifications, single additions/deletions) do not require it.
**Action:** Always defer expensive I/O operations in loops to the most specific conditional blocks where they are strictly necessary.

## 2026-03-24 - Optimize Path Resolution in Hot Loops
**Learning:** Unconditional `Path.resolve()` triggers expensive I/O operations (os.stat, os.readlink) in hot loops.
**Action:** Use memory-based checks like `path.is_relative_to(root)` as a fast path before falling back to `resolve()`.
