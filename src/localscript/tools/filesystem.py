from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path

IGNORED_DIRECTORY_NAMES = {
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
}


def list_workspace_paths(workspace_root: Path, pattern: str = "", limit: int = 50) -> dict[str, object]:
    normalized_pattern = pattern.lower().strip()
    paths: list[str] = []
    count = 0
    for file_path in _iter_workspace_files(workspace_root):
        relative_path = str(file_path.relative_to(workspace_root))
        if normalized_pattern and normalized_pattern not in relative_path.lower():
            continue
        count += 1
        if len(paths) < limit:
            paths.append(relative_path)
    return {"paths": paths, "count": count}


def search_workspace_text(
    workspace_root: Path, pattern: str, glob: str = "*.lua", limit: int = 20
) -> dict[str, object]:
    matcher = re.compile(pattern)
    hits: list[str] = []
    for file_path in _iter_workspace_files(workspace_root):
        relative_path = str(file_path.relative_to(workspace_root))
        if not fnmatch.fnmatch(relative_path, glob):
            continue
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_number, line_text in enumerate(lines, start=1):
            if matcher.search(line_text) is None:
                continue
            hits.append(f"{relative_path}:{line_number}:{line_text}")
            if len(hits) >= limit:
                return {
                    "pattern": pattern,
                    "hits": hits,
                    "exit_code": 0,
                }
    return {
        "pattern": pattern,
        "hits": hits,
        "exit_code": 0 if hits else 1,
    }


def _iter_workspace_files(workspace_root: Path):
    for current_root, directory_names, file_names in os.walk(workspace_root):
        directory_names[:] = sorted(name for name in directory_names if not _is_ignored_directory_name(name))
        current_path = Path(current_root)
        for file_name in sorted(file_names):
            if file_name.startswith("."):
                continue
            yield current_path / file_name


def _is_ignored_directory_name(name: str) -> bool:
    return name.startswith(".") or name in IGNORED_DIRECTORY_NAMES
