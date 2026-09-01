from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import urlparse

from gemini_cloner.util import ensure_dir, slugify, utc_now, which, write_json


class CloneError(RuntimeError):
    pass


def normalize_repo_url(url: str) -> str:
    raw = url.strip()
    if raw.endswith(".git"):
        raw = raw[:-4]
    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}.git"
    if raw.startswith("git@"):
        return raw if raw.endswith(".git") else raw + ".git"
    if "/" in raw and "://" not in raw:
        return f"https://github.com/{raw.strip('/')}.git"
    raise CloneError(f"Unrecognized repository URL: {url}")


def repo_slug(url: str) -> str:
    parsed = urlparse(normalize_repo_url(url).replace(".git", ""))
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2:
        return slugify(f"{parts[-2]}-{parts[-1]}")
    return slugify(parsed.path or parsed.netloc or "repo")


def clone_repo(url: str, dest_root: Path, depth: int = 1) -> dict:
    git = which("git")
    if not git:
        raise CloneError("git is not installed on PATH")

    source = normalize_repo_url(url)
    job_dir = ensure_dir(dest_root / repo_slug(url))
    worktree = job_dir / "source"
    if worktree.exists():
        raise CloneError(f"Clone already exists: {worktree}. Delete it or choose another name.")

    cmd = [git, "clone", "--depth", str(depth), "--single-branch", source, str(worktree)]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise CloneError(completed.stderr.strip() or completed.stdout.strip() or "git clone failed")

    meta = {
        "kind": "git",
        "source": source,
        "created_at": utc_now(),
        "depth": depth,
        "worktree": str(worktree),
        "stdout": completed.stdout.strip()[-2000:],
    }
    try:
        head = subprocess.run(
            [git, "-C", str(worktree), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        branch = subprocess.run(
            [git, "-C", str(worktree), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        remote = subprocess.run(
            [git, "-C", str(worktree), "remote", "-v"],
            capture_output=True,
            text=True,
            check=False,
        )
        meta["head"] = head.stdout.strip()
        meta["branch"] = branch.stdout.strip()
        meta["remotes"] = remote.stdout.strip()
    except OSError:
        pass
    write_json(job_dir / "job.json", meta)
    return meta
