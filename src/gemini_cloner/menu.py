from __future__ import annotations

import os
import threading
from pathlib import Path

from gemini_cloner import APP_NAME, BRAND, __version__
from gemini_cloner.backup import execute_plan, plan_backup
from gemini_cloner.config import settings
from gemini_cloner.consent import approval_url, make_job, require_approved, refresh_status, load_job, ConsentError
from gemini_cloner.consent_server import serve
from gemini_cloner.phone import detect_all, find_device, PhoneError
from gemini_cloner.sms import SmsError, configured as sms_configured, send_approval_sms
from gemini_cloner.util import which


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def _print_devices(devices: list[dict]) -> None:
    if not devices:
        print("No phones detected.")
        return
    for idx, device in enumerate(devices, 1):
        trust = "USB trusted" if device.get("usb_authorized") else "USB NOT trusted"
        print(f"  {idx}. {device['platform']:7} {device['serial']}  {device.get('model')}  {device.get('state')}  ({trust})")


def _start_server_if_needed(root: Path, host: str, port: int) -> None:
    marker = getattr(_start_server_if_needed, "_started", False)
    if marker:
        return
    server = serve(root, host, port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _start_server_if_needed._started = True
    print(f"Consent server listening on http://{host}:{port}")


def run_menu() -> int:
    cfg = settings()
    root = cfg.clone_root
    print(f"{APP_NAME} {__version__} — {BRAND}")
    print("Owner-authorized phone clone. SMS is only a short-lived approval link.")
    print("Passkey stays on the phone. USB trust is still mandatory.\n")
    while True:
        print("1) Doctor")
        print("2) Detect phones")
        print("3) Start clone job + consent link")
        print("4) Send / print SMS approval link")
        print("5) Check consent status")
        print("6) Execute approved clone (dry-run default)")
        print("7) Live execute approved clone")
        print("8) Public-source tools help")
        print("0) Quit")
        choice = _ask("Select", "0")
        try:
            if choice == "0":
                return 0
            if choice == "1":
                print({"adb": bool(which("adb")), "idevice_id": bool(which("idevice_id")), "idevicebackup2": bool(which("idevicebackup2")), "twilio": sms_configured(), "clone_root": str(root)})
            elif choice == "2":
                _print_devices(detect_all())
            elif choice == "3":
                devices = detect_all()
                _print_devices(devices)
                serial = _ask("Serial (blank if only one)")
                device = find_device(serial or None)
                phone = _ask("Owner phone number for SMS (E.164)", os.environ.get("GEMINI_OWNER_PHONE", ""))
                scope_raw = _ask("Scope comma-list", "media,documents,packages")
                scope = [part.strip() for part in scope_raw.split(",") if part.strip()]
                ttl = int(_ask("Link TTL minutes", "15"))
                base = os.environ.get("GEMINI_PUBLIC_BASE_URL", "http://127.0.0.1:8787")
                job = make_job(root, phone=phone or "unspecified", platform=device["platform"], serial=device["serial"], scope=scope, operator=os.environ.get("GEMINI_OPERATOR", "local-operator"), ttl_minutes=ttl, public_base=base)
                host, port = "0.0.0.0", int(os.environ.get("GEMINI_CONSENT_PORT", "8787"))
                _start_server_if_needed(root, host, port)
                print("Job created:")
                print(f"  id     {job['job_id']}")
                print(f"  expiry {job['expires_at']}")
                print(f"  link   {approval_url(job)}")
                print("Open that link on the OWNER phone. Then approve with passkey or the confirm button.")
                if phone and sms_configured():
                    send = _ask("Send SMS now? y/N", "N")
                    if send.lower().startswith("y"):
                        body = f"GEMINI owner consent for a scoped phone backup. This is not a login code. Approve only if you requested it. {approval_url(job)}"
                        print(send_approval_sms(phone, body))
            elif choice == "4":
                job_id = _ask("Job id")
                job = load_job(root, job_id)
                link = approval_url(job)
                print(link)
                if job.get("phone") and sms_configured():
                    print(send_approval_sms(job["phone"], f"GEMINI owner consent link (not a login code): {link}"))
                else:
                    print("SMS provider not configured; send the link yourself.")
            elif choice == "5":
                job_id = _ask("Job id")
                job = refresh_status(load_job(root, job_id))
                print({"status": job["status"], "serial": job["serial"], "scope": job["scope"], "expires_at": job["expires_at"]})
            elif choice in {"6", "7"}:
                job_id = _ask("Job id")
                job = require_approved(root, job_id)
                device = find_device(job["serial"])
                dest = root / "phone-clones" / job["job_id"]
                plan = plan_backup(device, job["scope"], dest)
                print(execute_plan(plan, dry_run=(choice == "6")))
            elif choice == "8":
                print("Non-phone commands: doctor, repo, web, tree, analyze, twin, report, phone, menu")
            else:
                print("Unknown selection")
        except (ConsentError, PhoneError, SmsError, ValueError) as exc:
            print(f"error: {exc}")
        print()
