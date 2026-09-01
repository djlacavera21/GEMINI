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
from gemini_cloner.phone import PhoneError, find_device
from gemini_cloner.report import render_report
from gemini_cloner.sms import SmsError, configured as sms_configured, send_approval_sms
from gemini_cloner.transport import connect_wifi, detect_by_transport, disconnect_wifi, enable_tcpip, pair_wireless, require_transport_trust
from gemini_cloner.tree_clone import CloneError as TreeCloneError
from gemini_cloner.tree_clone import clone_tree
from gemini_cloner.util import which
from gemini_cloner.web_clone import CloneError as WebCloneError
from gemini_cloner.web_clone import clone_web

def _print(payload):
    print(json.dumps(payload, indent=2, default=str))

def _fail(exc):
    print(f"error: {exc}", file=sys.stderr)
    return 2

def cmd_doctor(_):
    cfg = settings()
    _print({"app": APP_NAME, "version": __version__, "adb": bool(which("adb")), "idevice_id": bool(which("idevice_id")), "twilio_sms": sms_configured(), "clone_root": str(cfg.clone_root), "transports": ["usb", "wifi", "remote"]})
    return 0

def cmd_repo(args):
    try:
        _print(clone_repo(args.url, settings().clone_root, depth=args.depth))
    except GitCloneError as exc:
        return _fail(exc)
    return 0

def cmd_web(args):
    try:
        meta = clone_web(args.url, settings().clone_root, settings())
    except WebCloneError as exc:
        return _fail(exc)
    _print({k: v for k, v in meta.items() if k != "fetched"} | {"fetched_count": len(meta.get("fetched", []))})
    return 0

def cmd_tree(args):
    try:
        _print(clone_tree(Path(args.path), settings().clone_root))
    except TreeCloneError as exc:
        return _fail(exc)
    return 0

def cmd_analyze(args):
    try:
        print(analyze_job(Path(args.job), settings())["brief"])
    except Exception as exc:
        return _fail(exc)
    return 0

def cmd_twin(args):
    try:
        print(twin_job(Path(args.job), settings())["twin"])
    except Exception as exc:
        return _fail(exc)
    return 0

def cmd_report(args):
    try:
        print(render_report(Path(args.job)))
    except Exception as exc:
        return _fail(exc)
    return 0

def cmd_menu(_):
    return run_menu()

def cmd_phone_detect(_):
    _print(detect_by_transport())
    return 0

def cmd_phone_request(args):
    cfg = settings()
    try:
        device = find_device(args.serial)
        job = make_job(cfg.clone_root, phone=args.phone, platform=device["platform"], serial=device["serial"], scope=[s.strip() for s in args.scope.split(",") if s.strip()], operator=args.operator, ttl_minutes=args.ttl, public_base=args.public_base or os.environ.get("GEMINI_PUBLIC_BASE_URL", "http://127.0.0.1:8787"), transport=args.transport)
    except (PhoneError, ConsentError) as exc:
        return _fail(exc)
    payload = {"job_id": job["job_id"], "status": job["status"], "serial": job["serial"], "transport": job.get("transport"), "approval_url": approval_url(job), "expires_at": job["expires_at"], "scope": job["scope"]}
    _print(payload)
    if args.sms:
        try:
            _print(send_approval_sms(args.phone, "GEMINI owner consent. Not a login code. " + payload["approval_url"]))
        except SmsError as exc:
            return _fail(exc)
    return 0

def cmd_phone_status(args):
    try:
        job = refresh_status(load_job(settings().clone_root, args.job))
    except ConsentError as exc:
        return _fail(exc)
    _print({"job_id": job["job_id"], "status": job["status"], "transport": job.get("transport"), "expires_at": job["expires_at"]})
    return 0

def cmd_phone_serve(args):
    server = serve(settings().clone_root, args.host, args.port)
    print(f"consent server http://{args.host}:{args.port}/approve")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0

def cmd_phone_clone(args):
    cfg = settings()
    try:
        job = require_approved(cfg.clone_root, args.job)
        device = find_device(job["serial"])
        require_transport_trust(device, job.get("transport") or "usb")
        dest = Path(args.dest) if args.dest else cfg.clone_root / "phone-clones" / job["job_id"]
        _print(execute_plan(plan_backup(device, job["scope"], dest), dry_run=not args.live))
    except (ConsentError, PhoneError) as exc:
        return _fail(exc)
    return 0

def cmd_transport_list(_):
    _print(detect_by_transport())
    return 0

def cmd_transport_tcpip(args):
    try:
        _print(enable_tcpip(find_device(args.serial)["serial"], args.port))
    except PhoneError as exc:
        return _fail(exc)
    return 0

def cmd_transport_pair(args):
    try:
        _print(pair_wireless(args.host, args.port, args.code))
    except PhoneError as exc:
        return _fail(exc)
    return 0

def cmd_transport_connect(args):
    try:
        _print(connect_wifi(args.host, args.port))
    except PhoneError as exc:
        return _fail(exc)
    return 0

def cmd_transport_disconnect(args):
    try:
        _print(disconnect_wifi(args.host, args.port))
    except PhoneError as exc:
        return _fail(exc)
    return 0

def build_parser():
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
    p.add_argument("--transport", choices=["usb", "wifi", "remote"], default="usb")
    p.add_argument("--ttl", type=int, default=15)
    p.add_argument("--operator", default=os.environ.get("GEMINI_OPERATOR", "local-operator"))
    p.add_argument("--public-base", dest="public_base", default="")
    p.add_argument("--sms", action="store_true")
    p.set_defaults(func=cmd_phone_request)
    p = phone_sub.add_parser("status"); p.add_argument("job"); p.set_defaults(func=cmd_phone_status)
    p = phone_sub.add_parser("serve"); p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=8787); p.set_defaults(func=cmd_phone_serve)
    p = phone_sub.add_parser("clone"); p.add_argument("job"); p.add_argument("--live", action="store_true"); p.add_argument("--dest"); p.set_defaults(func=cmd_phone_clone)
    transport = phone_sub.add_parser("transport")
    tsub = transport.add_subparsers(dest="transport_command", required=True)
    p = tsub.add_parser("list"); p.set_defaults(func=cmd_transport_list)
    p = tsub.add_parser("tcpip"); p.add_argument("--serial"); p.add_argument("--port", type=int, default=5555); p.set_defaults(func=cmd_transport_tcpip)
    p = tsub.add_parser("pair"); p.add_argument("--host", required=True); p.add_argument("--port", type=int, required=True); p.add_argument("--code", required=True); p.set_defaults(func=cmd_transport_pair)
    p = tsub.add_parser("connect"); p.add_argument("--host", required=True); p.add_argument("--port", type=int, default=5555); p.set_defaults(func=cmd_transport_connect)
    p = tsub.add_parser("disconnect"); p.add_argument("--host", required=True); p.add_argument("--port", type=int, default=5555); p.set_defaults(func=cmd_transport_disconnect)
    return parser

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        return run_menu()
    return int(args.func(args))
