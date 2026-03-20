## 2026-03-20 - Optimize File Change Coalescing
**Learning:** Checking file existence using `Path.exists()` is a costly I/O operation. Performing this check for every file in a watch batch significantly impacts performance, especially when most changes (modifications, single additions/deletions) do not require it.
**Action:** Always defer expensive I/O operations in loops to the most specific conditional blocks where they are strictly necessary.

## 2026-05-18 - Avoid Path.resolve() in High-Frequency Loops
**Learning:** `Path.resolve()` is extremely expensive in Python hot loops (like file watching or directory scanning) because it triggers multiple system calls (`os.stat`, `os.readlink`, etc.) to resolve symlinks and absolute paths. In cases where paths are largely already absolute and descendants of a known root, resolving every path unconditionally is a major bottleneck.
**Action:** Use a fast-path check like `path.is_relative_to(root)` before falling back to `path.resolve(strict=False)` to skip expensive system calls for the vast majority of files.
