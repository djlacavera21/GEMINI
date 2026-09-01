from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from gemini_cloner.phone import PhoneError, require_usb_trust
from gemini_cloner.util import ensure_dir, utc_now, which, write_json


ANDROID_PATHS = {
    "media": ["/sdcard/DCIM", "/sdcard/Pictures", "/sdcard/Download"],
    "documents": ["/sdcard/Documents", "/sdcard/Download"],
}


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def plan_backup(device: dict[str, Any], scope: list[str], dest: Path) -> dict[str, Any]:
    require_usb_trust(device)
    actions: list[dict[str, Any]] = []
    platform = device["platform"]
    if platform == "android":
        if not which("adb"):
            raise PhoneError("adb is required for Android clones")
        if "packages" in scope:
            actions.append({"kind": "packages", "cmd": ["adb", "-s", device["serial"], "shell", "pm", "list", "packages"]})
        for key in ("media", "documents"):
            if key in scope:
                for remote in ANDROID_PATHS[key]:
                    actions.append(
                        {
                            "kind": "pull",
                            "remote": remote,
                            "local": str(dest / key / Path(remote).name),
                            "cmd": ["adb", "-s", device["serial"], "pull", remote, str(dest / key / Path(remote).name)],
                        }
                    )
        if "adb_backup" in scope:
            actions.append(
                {
                    "kind": "adb_backup",
                    "note": "Android will show an on-device backup confirmation. This tool will not bypass it.",
                    "cmd": ["adb", "-s", device["serial"], "backup", "-f", str(dest / "android-backup.ab"), "-apk", "-shared", "-all"],
                }
            )
        if "sms_export" in scope:
            actions.append(
                {
                    "kind": "sms_export",
                    "note": "SMS export requires an on-device export app or owner-granted extra permissions. GEMINI will not scrape the SMS provider without that.",
                    "cmd": None,
                }
            )
    elif platform == "ios":
        if "ios_backup" not in scope and set(scope) & {"media", "documents", "adb_backup"}:
            actions.append({"kind": "ios_backup", "note": "iOS scoped file pulls are not supported without a trusted encrypted backup."})
        if not which("idevicebackup2"):
            raise PhoneError("idevicebackup2 (libimobiledevice) is required for iPhone clones")
        actions.append(
            {
                "kind": "ios_backup",
                "cmd": ["idevicebackup2", "-u", device["serial"], "backup", str(dest)],
                "note": "Trust This Computer must already be accepted. Encrypted backups stay encrypted unless you supply the owner password later.",
            }
        )
    else:
        raise PhoneError(f"Unsupported platform {platform}")
    return {
        "device": device,
        "scope": scope,
        "dest": str(dest),
        "actions": actions,
        "created_at": utc_now(),
    }


def execute_plan(plan: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
    dest = ensure_dir(Path(plan["dest"]))
    results = []
    for action in plan["actions"]:
        record = {"kind": action["kind"], "dry_run": dry_run, "note": action.get("note")}
        cmd = action.get("cmd")
        if dry_run or not cmd:
            record["status"] = "planned"
            record["cmd"] = cmd
            results.append(record)
            continue
        if action["kind"] == "pull":
            ensure_dir(Path(action["local"]).parent)
        completed = _run(cmd, timeout=600)
        record["cmd"] = cmd
        record["returncode"] = completed.returncode
        record["stdout"] = (completed.stdout or "")[-2000:]
        record["stderr"] = (completed.stderr or "")[-2000:]
        record["status"] = "ok" if completed.returncode == 0 else "failed"
        results.append(record)
    summary = {
        "finished_at": utc_now(),
        "dry_run": dry_run,
        "results": results,
        "dest": str(dest),
    }
    write_json(dest / "backup-result.json", summary)
    return summary
