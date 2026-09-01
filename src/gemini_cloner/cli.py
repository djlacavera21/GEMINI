from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gemini_cloner import APP_NAME, BRAND, __version__
from gemini_cloner.analyze import analyze_job, twin_job
from gemini_cloner.config import settings
from gemini_cloner.git_clone import CloneError as GitCloneError
from gemini_cloner.git_clone import clone_repo
from gemini_cloner.report import render_report
from gemini_cloner.tree_clone import CloneError as TreeCloneError
from gemini_cloner.tree_clone import clone_tree
from gemini_cloner.util import which
from gemini_cloner.web_clone import CloneError as WebCloneError
from gemini_cloner.web_clone import clone_web


def _print(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


def cmd_doctor(_: argparse.Namespace) -> int:
    cfg = settings()
    info = {
        "app": APP_NAME,
        "brand": BRAND,
        "version": __version__,
        "git": bool(which("git")),
        "clone_root": str(cfg.clone_root),
        "model": cfg.model,
        "gemini_key_present": bool(cfg.api_key),
        "web_max_pages": cfg.web_max_pages,
        "web_max_bytes": cfg.web_max_bytes,
    }
    _print(info)
    if not info["git"]:
        print("warning: git is required for `repo` clones", file=sys.stderr)
    if not info["gemini_key_present"]:
        print("warning: GEMINI_API_KEY missing; analyze/twin disabled", file=sys.stderr)
    return 0


def cmd_repo(args: argparse.Namespace) -> int:
    cfg = settings()
    try:
        meta = clone_repo(args.url, cfg.clone_root, depth=args.depth)
    except GitCloneError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _print(meta)
    return 0


def cmd_web(args: argparse.Namespace) -> int:
    cfg = settings()
    try:
        meta = clone_web(args.url, cfg.clone_root, cfg)
    except WebCloneError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _print({k: v for k, v in meta.items() if k != "fetched"} | {"fetched_count": len(meta.get("fetched", []))})
    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    cfg = settings()
    try:
        meta = clone_tree(Path(args.path), cfg.clone_root)
    except TreeCloneError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _print(meta)
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    cfg = settings()
    try:
        payload = analyze_job(Path(args.job), cfg)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(payload["brief"])
    print(f"\n[wrote {Path(args.job).resolve()}/ANALYSIS.md]", file=sys.stderr)
    return 0


def cmd_twin(args: argparse.Namespace) -> int:
    cfg = settings()
    try:
        payload = twin_job(Path(args.job), cfg)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(payload["twin"])
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    try:
        text = render_report(Path(args.job))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gemini-cloner",
        description=f"{APP_NAME} — {BRAND}",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="Show local capability and configuration")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("repo", help="Shallow-clone a public Git repository")
    p.add_argument("url", help="https URL, git@ URL, or owner/name")
    p.add_argument("--depth", type=int, default=1)
    p.set_defaults(func=cmd_repo)

    p = sub.add_parser("web", help="Bounded same-host public web snapshot")
    p.add_argument("url")
    p.set_defaults(func=cmd_web)

    p = sub.add_parser("tree", help="Copy a local file or directory into the clone root")
    p.add_argument("path")
    p.set_defaults(func=cmd_tree)

    p = sub.add_parser("analyze", help="Gemini brief of an existing clone job")
    p.add_argument("job", help="Path to the job directory (contains job.json)")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("twin", help="Gemini clean-room reconstruction brief")
    p.add_argument("job")
    p.set_defaults(func=cmd_twin)

    p = sub.add_parser("report", help="Write REPORT.md for a clone job")
    p.add_argument("job")
    p.set_defaults(func=cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
