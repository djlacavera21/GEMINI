from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from gemini_cloner import APP_NAME, BRAND, __version__
from gemini_cloner.analyze import analyze_job, twin_job
from gemini_cloner.backup import execute_plan, plan_backup
from gemini_cloner.config import settings
from gemini_cloner.consent import ConsentError, approval_url, load_job, make_job, refresh_status, require_approved
from gemini_cloner.consent_server import serve
from gemini_cloner.git_clone import CloneError as GitCloneError
from gemini_cloner.git_clone import clone_repo
from gemini_cloner.menu import run_menu
from gemini_cloner.phone import PhoneError, detect_all, find_device
from gemini_cloner.report import render_report
from gemini_cloner.sms import SmsError, configured as sms_configured, send_approval_sms
from gemini_cloner.tree_clone import CloneError as TreeCloneError
from gemini_cloner.tree_clone import clone_tree
from gemini_cloner.util import which
from gemini_cloner.web_clone import CloneError as WebCloneError
from gemini_cloner.web_clone import clone_web


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, default=str))


def cmd_doctor(_: argparse.Namespace) -> int:
    cfg = settings()
    info = {
        "app": APP_NAME,
        "brand": BRAND,
        "version": __version__,
        "git": bool(which("git")),
        "adb": bool(which("adb")),
        "idevice_id": bool(which("idevice_id")),
        "idevicebackup2": bool(which("idevicebackup2")),
        "twilio_sms": sms_configured(),
        "clone_root": str(cfg.clone_root),
        "model": cfg.model,
        "gemini_key_present": bool(cfg.api_key),
    }
    _print(info)
    return 0


def cmd_repo(args: argparse.Namespace) -> int:
    try:
        _print(clone_repo(args.url, settings().clone_root, depth=args.depth))
    except GitCloneError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_web(args: argparse.Namespace) -> int:
    try:
        meta = clone_web(args.url, settings().clone_root, settings())
    except WebCloneError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _print({k: v for k, v in meta.items() if k != "fetched"} | {"fetched_count": len(meta.get("fetched", []))})
    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    try:
        _print(clone_tree(Path(args.path), settings().clone_root))
    except TreeCloneError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        print(analyze_job(Path(args.job), settings())["brief"])
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_twin(args: argparse.Namespace) -> int:
    try:
        print(twin_job(Path(args.job), settings())["twin"])
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    try:
        print(render_report(Path(args.job)))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_menu(_: argparse.Namespace) -> int:
    return run_menu()


def cmd_phone_detect(_: argparse.Namespace) -> int:
    _print(detect_all())
    return 0


def cmd_phone_request(args: argparse.Namespace) -> int:
    cfg = settings()
    try:
        device = find_device(args.serial)
        scope = [part.strip() for part in args.scope.split(",") if part.strip()]
        base = args.public_base or os.environ.get("GEMINI_PUBLIC_BASE_URL", "http://127.0.0.1:8787")
        job = make_job(cfg.clone_root, phone=args.phone, platform=device["platform"], serial=device["serial"], scope=scope, operator=args.operator, ttl_minutes=args.ttl, public_base=base)
    except (PhoneError, ConsentError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload = {"job_id": job["job_id"], "status": job["status"], "expires_at": job["expires_at"], "serial": job["serial"], "scope": job["scope"], "approval_url": approval_url(job)}
    _print(payload)
    if args.sms:
        try:
            _print(send_approval_sms(args.phone, "GEMINI owner consent for a scoped phone backup. Not a login code. " + payload["approval_url"]))
        except SmsError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    return 0


def cmd_phone_status(args: argparse.Namespace) -> int:
    try:
        job = refresh_status(load_job(settings().clone_root, args.job))
    except ConsentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _print({"job_id": job["job_id"], "status": job["status"], "expires_at": job["expires_at"], "scope": job["scope"]})
    return 0


def cmd_phone_serve(args: argparse.Namespace) -> int:
    server = serve(settings().clone_root, args.host, args.port)
    print(f"consent server http://{args.host}:{args.port}/approve")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


def cmd_phone_clone(args: argparse.Namespace) -> int:
    cfg = settings()
    try:
        job = require_approved(cfg.clone_root, args.job)
        device = find_device(job["serial"])
        dest = Path(args.dest) if args.dest else cfg.clone_root / "phone-clones" / job["job_id"]
        result = execute_plan(plan_backup(device, job["scope"], dest), dry_run=not args.live)
    except (ConsentError, PhoneError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _print(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gemini-cloner", description=f"{APP_NAME} — {BRAND}")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("menu"); p.set_defaults(func=cmd_menu)
    p = sub.add_parser("doctor"); p.set_defaults(func=cmd_doctor)
    p = sub.add_parser("repo"); p.add_argument("url"); p.add_argument("--depth", type=int, default=1); p.set_defaults(func=cmd_repo)
    p = sub.add_parser("web"); p.add_argument("url"); p.set_defaults(func=cmd_web)
    p = sub.add_parser("tree"); p.add_argument("path"); p.set_defaults(func=cmd_tree)
    p = sub.add_parser("analyze"); p.add_argument("job"); p.set_defaults(func=cmd_analyze)
    p = sub.add_parser("twin"); p.add_argument("job"); p.set_defaults(func=cmd_twin)
    p = sub.add_parser("report"); p.add_argument("job"); p.set_defaults(func=cmd_report)
    phone = sub.add_parser("phone")
    phone_sub = phone.add_subparsers(dest="phone_command", required=True)
    p = phone_sub.add_parser("detect"); p.set_defaults(func=cmd_phone_detect)
    p = phone_sub.add_parser("request")
    p.add_argument("--phone", required=True)
    p.add_argument("--serial")
    p.add_argument("--scope", default="media,documents,packages")
    p.add_argument("--ttl", type=int, default=15)
    p.add_argument("--operator", default=os.environ.get("GEMINI_OPERATOR", "local-operator"))
    p.add_argument("--public-base", dest="public_base", default="")
    p.add_argument("--sms", action="store_true")
    p.set_defaults(func=cmd_phone_request)
    p = phone_sub.add_parser("status"); p.add_argument("job"); p.set_defaults(func=cmd_phone_status)
    p = phone_sub.add_parser("serve"); p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=8787); p.set_defaults(func=cmd_phone_serve)
    p = phone_sub.add_parser("clone"); p.add_argument("job"); p.add_argument("--live", action="store_true"); p.add_argument("--dest"); p.set_defaults(func=cmd_phone_clone)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        return run_menu()
    return int(args.func(args))
