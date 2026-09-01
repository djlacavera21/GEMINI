from __future__ import annotations

import shutil
from pathlib import Path

from gemini_cloner.util import ensure_dir, slugify, utc_now, write_json


class CloneError(RuntimeError):
    pass


SKIP_DIR_NAMES = {".git", ".venv", "node_modules", "__pycache__", ".tox", "dist", "build"}


def clone_tree(src: Path, dest_root: Path) -> dict:
    src = src.expanduser().resolve()
    if not src.exists():
        raise CloneError(f"Source path does not exist: {src}")
    job_dir = ensure_dir(dest_root / slugify(src.name))
    worktree = job_dir / "source"
    if worktree.exists():
        raise CloneError(f"Clone already exists: {worktree}")

    if src.is_file():
        ensure_dir(worktree)
        shutil.copy2(src, worktree / src.name)
        files = 1
    else:
        def ignore(directory: str, names: list[str]) -> set[str]:
            return {name for name in names if name in SKIP_DIR_NAMES}

        shutil.copytree(src, worktree, ignore=ignore)
        files = sum(1 for path in worktree.rglob("*") if path.is_file())

    meta = {
        "kind": "tree",
        "source": str(src),
        "created_at": utc_now(),
        "files": files,
        "worktree": str(worktree),
    }
    write_json(job_dir / "job.json", meta)
    return meta
