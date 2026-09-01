from __future__ import annotations

from pathlib import Path

from gemini_cloner.util import human_bytes, read_json, utc_now


def render_report(job_dir: Path) -> str:
    job_dir = job_dir.expanduser().resolve()
    job = read_json(job_dir / "job.json")
    analysis = None
    twin = None
    if (job_dir / "analysis.json").is_file():
        analysis = read_json(job_dir / "analysis.json")
    twin_json = job_dir / "twin" / "twin.json"
    if twin_json.is_file():
        twin = read_json(twin_json)

    lines = [
        f"# GEMINI clone report",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Kind: `{job.get('kind')}`",
        f"- Source: `{job.get('source')}`",
        f"- Created: `{job.get('created_at')}`",
        f"- Worktree: `{job.get('worktree')}`",
    ]
    if job.get("head"):
        lines.append(f"- HEAD: `{job.get('head')}`")
    if job.get("pages") is not None:
        lines.append(f"- Pages fetched: `{job.get('pages')}`")
        lines.append(f"- Bytes: `{human_bytes(int(job.get('bytes') or 0))}`")
    if job.get("files") is not None:
        lines.append(f"- Files copied: `{job.get('files')}`")
    lines.append("")
    if analysis:
        lines.append("## Analysis")
        lines.append("")
        lines.append(analysis.get("brief", "").strip())
        lines.append("")
    if twin:
        lines.append("## Twin brief")
        lines.append("")
        lines.append(twin.get("twin", "").strip())
        lines.append("")
    lines.append("## Safety")
    lines.append("")
    lines.append("This report is a local research artifact. It is not a license to redistribute third-party code.")
    text = "\n".join(lines) + "\n"
    (job_dir / "REPORT.md").write_text(text, encoding="utf-8")
    return text
