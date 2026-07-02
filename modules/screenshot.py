from __future__ import annotations
import os
from pathlib import Path

from .consts import FILETYPES, SCR_DIR


def is_thumbnail(path: Path) -> bool: return any(part.lower() == "thumbnails" for part in path.parts)

# get the latest deadlock screenshot and roll with it
# could technically search multiple directories
def find_latest_scr(roots: Path | list[Path] | None = None) -> Path:
    if roots is None:
        search_roots = [SCR_DIR]
    elif isinstance(roots, Path):
        search_roots = [roots]
    else:
        search_roots = roots
    candidates: list[Path] = []

    for root in search_roots:
        if any(part == "*" for part in root.parts):
            candidates.extend(_glob_images(root))
            continue

        if root.is_file() and root.suffix.lower() in FILETYPES:
            if not is_thumbnail(root): candidates.append(root)
            continue

        if root.is_dir():
            candidates.extend(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in FILETYPES and not is_thumbnail(path)
            )

    if not candidates: raise FileNotFoundError("Couldn't find any screenshots")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _glob_images(root: Path) -> list[Path]:
    matched: list[Path] = []
    base_parts = []
    for part in root.parts:
        if part == "*": break
        base_parts.append(part)

    base = Path(*base_parts)
    tail = root.parts[len(base_parts) :]
    if not base.exists(): return matched

    for candidate in base.glob(str(Path(*tail))):
        if candidate.is_file() and candidate.suffix.lower() in FILETYPES:
            if not is_thumbnail(candidate): matched.append(candidate)
        elif candidate.is_dir():
            matched.extend(
                path
                for path in candidate.rglob("*")
                if path.is_file() and path.suffix.lower() in FILETYPES and not is_thumbnail(path)
            )

    return matched
