## 2026-03-20 - Optimize File Change Coalescing
**Learning:** Checking file existence using `Path.exists()` is a costly I/O operation. Performing this check for every file in a watch batch significantly impacts performance, especially when most changes (modifications, single additions/deletions) do not require it.
**Action:** Always defer expensive I/O operations in loops to the most specific conditional blocks where they are strictly necessary.

## 2026-03-20 - Optimize Path Resolution in Hot Loops
**Learning:** In Python hot loops (like file event processing in `nomnom/watcher.py`), unconditionally calling `Path.resolve()` is extremely expensive as it triggers system filesystem operations (`os.stat`, `os.readlink`).
**Action:** Implement fast paths using memory-based checks, such as using `path.is_absolute()` and `path.is_relative_to(root)`, to bypass `resolve()` entirely when paths are already properly formed absolute paths.
