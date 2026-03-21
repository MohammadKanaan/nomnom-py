## 2026-03-20 - Optimize File Change Coalescing
**Learning:** Checking file existence using `Path.exists()` is a costly I/O operation. Performing this check for every file in a watch batch significantly impacts performance, especially when most changes (modifications, single additions/deletions) do not require it.
**Action:** Always defer expensive I/O operations in loops to the most specific conditional blocks where they are strictly necessary.

## 2024-03-21 - Avoid Path.resolve() in hot loops
**Learning:** In Python hot loops (like file watching or directory scanning), unconditionally calling `Path.resolve()` triggers expensive filesystem operations (`os.stat`, `os.readlink`).
**Action:** Implement a fast path using memory-based checks like `path.is_relative_to(root)` before falling back to `resolve()`.
