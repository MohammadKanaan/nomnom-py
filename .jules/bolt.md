## 2025-02-19 - Exception Handling in Hot Loops
**Learning:** Using exceptions (like `try/except ValueError:`) for normal control flow in hot loops is extremely slow in Python compared to boolean condition checks, especially when many exceptions will be raised and caught. This pattern was found in `_resolve_group()` when determining if paths were inside watch group directories.
**Action:** Always prefer boolean condition checks over exception handling in high-frequency loops, such as replacing `try: p.relative_to(root)` with `if p.is_relative_to(root)`.
