## 2026-03-20 - Optimize File Change Coalescing
**Learning:** Checking file existence using `Path.exists()` is a costly I/O operation. Performing this check for every file in a watch batch significantly impacts performance, especially when most changes (modifications, single additions/deletions) do not require it.
**Action:** Always defer expensive I/O operations in loops to the most specific conditional blocks where they are strictly necessary.

## 2026-03-27 - Optimize File Append Operations
**Learning:** Reading entire files into memory just to append content incurs O(N) I/O and memory overhead relative to the file size. This degrades performance significantly for large files.
**Action:** Always use binary append mode (`open('ab')`) for file appends to achieve O(1) complexity.
