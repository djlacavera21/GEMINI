from __future__ import annotations

from pathlib import Path

from gemini_cloner.config import Settings
from gemini_cloner.gemini import generate
from gemini_cloner.util import human_bytes, read_json, utc_now, write_json


TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".rs",
    ".go",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".html",
    ".css",
    ".sh",
    ".ini",
    ".cfg",
    ".c",
    ".h",
    ".cpp",
    ".java",
    ".rb",
    ".php",
}


SKIP_DIR = {".git", ".venv", "node_modules", "__pycache__", "dist", "build"}


def job_dir_from(path: Path) -> Path:
    path = path.expanduser().resolve()
    if (path / "job.json").is_file():
        return path
    if (path.parent / "job.json").is_file():
        return path.parent
    raise FileNotFoundError(f"No job.json found at {path} or its parent")


def inventory(worktree: Path, limit_files: int = 80, max_chars: int = 24_000) -> dict:
    files: list[dict] = []
    samples: list[str] = []
    total = 0
    bytes_total = 0
    for item in sorted(worktree.rglob("*")):
        if any(part in SKIP_DIR for part in item.parts):
            continue
        if not item.is_file():
            continue
        total += 1
        size = item.stat().st_size
        bytes_total += size
        rel = str(item.relative_to(worktree))
        files.append({"path": rel, "bytes": size, "suffix": item.suffix.lower()})
        if len(samples) < 18 and item.suffix.lower() in TEXT_SUFFIXES and size < 120_000:
            try:
                text = item.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            snippet = text[:1800]
            samples.append(f"## {rel}\n{snippet}")
        if len(files) >= limit_files:
            break
    blob = "\n\n".join(samples)
    return {
        "file_count_seen": total,
        "bytes": bytes_total,
        "files": files[:limit_files],
        "sample": blob[:max_chars],
    }


def analyze_job(job_path: Path, settings: Settings) -> dict:
    job_dir = job_dir_from(job_path)
    job = read_json(job_dir / "job.json")
    worktree = Path(job.get("worktree") or (job_dir / "source"))
    if not worktree.exists():
        raise FileNotFoundError(f"Worktree missing: {worktree}")
    inv = inventory(worktree)
    prompt = f"""You are analyzing a locally cloned public source for research notes.

Clone kind: {job.get('kind')}
Source: {job.get('source')}
Created: {job.get('created_at')}
Files sampled: {inv['file_count_seen']}
Bytes sampled: {inv['bytes']}

File list:
{inv['files']}

Selected text excerpts:
{inv['sample']}

Write a structured brief with these headings:
1. What this source is
2. Layout and notable files
3. Apparent purpose / stack
4. Risks, licenses, or missing pieces
5. Suggested next research steps

Do not invent APIs, secrets, or files that are not in the excerpts.
Do not provide instructions for breaking into systems, bypassing auth, or copying proprietary binaries for redistribution.
"""
    brief = generate(settings, prompt)
    payload = {
        "created_at": utc_now(),
        "job": job,
        "inventory": {
            "file_count_seen": inv["file_count_seen"],
            "bytes": inv["bytes"],
            "bytes_human": human_bytes(inv["bytes"]),
            "files": inv["files"],
        },
        "brief": brief,
        "model": settings.model,
    }
    write_json(job_dir / "analysis.json", payload)
    (job_dir / "ANALYSIS.md").write_text(brief + "\n", encoding="utf-8")
    return payload


def twin_job(job_path: Path, settings: Settings) -> dict:
    job_dir = job_dir_from(job_path)
    analysis_path = job_dir / "analysis.json"
    if analysis_path.is_file():
        analysis = read_json(analysis_path)
        brief = analysis.get("brief", "")
        job = analysis.get("job") or read_json(job_dir / "job.json")
    else:
        analysis = analyze_job(job_dir, settings)
        brief = analysis["brief"]
        job = analysis["job"]

    prompt = f"""Turn the following research brief into a reconstruction plan — a twin brief — for an original project inspired by the clone.

This is not a request to pirate, crack, or republish third-party proprietary code.
Produce:
- Working title
- Problem statement
- Original architecture that could be built clean-room
- Module list
- MVP milestone list
- Explicit things that must NOT be copied verbatim from the source

Source: {job.get('source')}
Kind: {job.get('kind')}

Brief:
{brief}
"""
    twin = generate(settings, prompt)
    payload = {
        "created_at": utc_now(),
        "source": job.get("source"),
        "twin": twin,
        "model": settings.model,
    }
    twins_dir = job_dir / "twin"
    twins_dir.mkdir(exist_ok=True)
    write_json(twins_dir / "twin.json", payload)
    (twins_dir / "TWIN.md").write_text(twin + "\n", encoding="utf-8")
    return payload
