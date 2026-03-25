from pathlib import Path


def validate_plugin_name(name: str) -> str:
    """Validate and normalize a plugin name into a safe slug."""
    normalized = name.strip()
    if not normalized:
        raise ValueError("Plugin name cannot be empty")

    if "/" in normalized or "\\" in normalized:
        raise ValueError("Plugin name cannot contain path separators")

    if ".." in normalized:
        raise ValueError("Plugin name cannot contain '..'")

    if normalized.startswith("~") or normalized.startswith("/"):
        raise ValueError("Plugin name cannot be an absolute path")

    slug = normalized.lower().replace("_", "-")
    if not all(char.isalnum() or char == "-" for char in slug):
        raise ValueError("Plugin name can only contain letters, numbers, underscores, and hyphens")

    return slug


def _is_subpath(path: Path, parent: Path) -> bool:
    return path.is_relative_to(parent)


def validate_module_path_containment(plugin_root: Path, module_path: str) -> Path | None:
    """Resolve module path to a Python file only if it remains in plugin_root."""
    if not module_path or ":" in module_path:
        return None

    if module_path.startswith("/") or module_path.startswith("~"):
        return None

    if len(module_path) > 2 and module_path[1] == ":" and module_path[0].isalpha():
        return None

    parts = module_path.split(".")
    if any(part in ("", ".", "..") for part in parts):
        return None

    root_resolved = plugin_root.resolve()
    module_file = plugin_root / Path(*parts[:-1]) / f"{parts[-1]}.py"
    package_init = plugin_root / Path(*parts) / "__init__.py"

    candidates = [module_file, package_init]

    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if _is_subpath(resolved, root_resolved):
            return resolved

    return None
