from __future__ import annotations

import shutil
import subprocess
from typing import Any


class PhoneError(RuntimeError):
    pass


def _run(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def detect_android() -> list[dict[str, Any]]:
    if not shutil.which("adb"):
        return []
    completed = _run(["adb", "devices", "-l"])
    devices: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        extras = {}
        for item in parts[2:]:
            if ":" in item:
                key, value = item.split(":", 1)
                extras[key] = value
        devices.append(
            {
                "platform": "android",
                "serial": serial,
                "state": state,
                "model": extras.get("model") or extras.get("device") or "android",
                "product": extras.get("product"),
                "usb_authorized": state == "device",
                "tool": "adb",
            }
        )
    return devices


def detect_ios() -> list[dict[str, Any]]:
    if not shutil.which("idevice_id"):
        return []
    completed = _run(["idevice_id", "-l"])
    devices: list[dict[str, Any]] = []
    for serial in completed.stdout.splitlines():
        serial = serial.strip()
        if not serial:
            continue
        info = {"platform": "ios", "serial": serial, "model": "iphone", "tool": "libimobiledevice"}
        if shutil.which("ideviceinfo"):
            raw = _run(["ideviceinfo", "-u", serial, "-k", "ProductType"])
            if raw.returncode == 0 and raw.stdout.strip():
                info["model"] = raw.stdout.strip()
            pair = _run(["idevicepair", "validate", "-u", serial]) if shutil.which("idevicepair") else None
            info["usb_authorized"] = bool(pair and pair.returncode == 0)
            info["state"] = "paired" if info.get("usb_authorized") else "untrusted"
        else:
            info["usb_authorized"] = False
            info["state"] = "detected"
        devices.append(info)
    return devices


def detect_all() -> list[dict[str, Any]]:
    return detect_android() + detect_ios()


def require_usb_trust(device: dict[str, Any]) -> dict[str, Any]:
    if not device.get("usb_authorized"):
        platform = device.get("platform")
        hint = (
            "Unlock the Android phone and accept the RSA / 'Allow USB debugging' prompt."
            if platform == "android"
            else "Unlock the iPhone and tap Trust This Computer."
        )
        raise PhoneError(
            f"Device {device.get('serial')} is not USB-authorized ({device.get('state')}). {hint} "
            "Owner SMS/passkey consent cannot replace that OS prompt."
        )
    return device


def find_device(serial: str | None) -> dict[str, Any]:
    devices = detect_all()
    if not devices:
        raise PhoneError(
            "No phones detected. Plug in USB, enable Developer Mode / USB debugging, "
            "and install adb and/or libimobiledevice."
        )
    if serial:
        for device in devices:
            if device["serial"] == serial:
                return device
        raise PhoneError(f"Serial {serial} not found. Seen: {[d['serial'] for d in devices]}")
    if len(devices) == 1:
        return devices[0]
    raise PhoneError(f"Multiple phones detected; pass --serial. Seen: {devices}")
