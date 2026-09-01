from __future__ import annotations

import ipaddress
import shutil
from typing import Any

from gemini_cloner.phone import PhoneError, _run, detect_all


TRANSPORTS = ("usb", "wifi", "remote")


def classify_serial(serial: str) -> str:
    if ":" in serial:
        return "wifi"
    return "usb"


def tag_device(device: dict[str, Any]) -> dict[str, Any]:
    out = dict(device)
    out["transport"] = classify_serial(str(device.get("serial") or ""))
    return out


def detect_by_transport() -> dict[str, list[dict[str, Any]]]:
    devices = [tag_device(item) for item in detect_all()]
    return {
        "usb": [d for d in devices if d["transport"] == "usb"],
        "wifi": [d for d in devices if d["transport"] == "wifi"],
        "all": devices,
    }


def _require_adb() -> str:
    path = shutil.which("adb")
    if not path:
        raise PhoneError("adb is required for USB and remote Android transports")
    return path


def _valid_host(host: str) -> str:
    host = host.strip()
    if not host:
        raise PhoneError("Host is required")
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        if all(part.replace("-", "").isalnum() for part in host.split(".")) and "." in host:
            return host
        raise PhoneError(f"Refusing host {host!r}; use an IP or simple hostname")


def enable_tcpip(serial: str, port: int = 5555) -> dict[str, Any]:
    """USB step: ask an already-trusted USB device to listen on TCP."""
    _require_adb()
    if ":" in serial:
        raise PhoneError("tcpip enable must target a USB serial, not host:port")
    completed = _run(["adb", "-s", serial, "tcpip", str(port)])
    if completed.returncode != 0:
        raise PhoneError(completed.stderr.strip() or "adb tcpip failed")
    return {"serial": serial, "listen_port": port, "transport": "wifi", "stdout": completed.stdout.strip()}


def pair_wireless(host: str, port: int, code: str) -> dict[str, Any]:
    """Android 11+ wireless debugging pairing. Code is shown on the owner phone."""
    _require_adb()
    host = _valid_host(host)
    code = code.strip()
    if not code.isdigit() or len(code) < 6:
        raise PhoneError("Wireless pairing code must be the digits shown on the phone")
    target = f"{host}:{int(port)}"
    completed = _run(["adb", "pair", target, code])
    if completed.returncode != 0:
        raise PhoneError(completed.stderr.strip() or f"adb pair {target} failed")
    return {"target": target, "paired": True, "stdout": completed.stdout.strip()}


def connect_wifi(host: str, port: int = 5555) -> dict[str, Any]:
    _require_adb()
    host = _valid_host(host)
    target = f"{host}:{int(port)}"
    completed = _run(["adb", "connect", target])
    text = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0 or "failed" in text.lower() or "refused" in text.lower():
        raise PhoneError(text or f"adb connect {target} failed")
    return {"target": target, "transport": "wifi", "stdout": text}


def disconnect_wifi(host: str, port: int = 5555) -> dict[str, Any]:
    _require_adb()
    target = f"{_valid_host(host)}:{int(port)}"
    completed = _run(["adb", "disconnect", target])
    return {"target": target, "stdout": (completed.stdout + completed.stderr).strip()}


def require_transport_trust(device: dict[str, Any], wanted: str) -> dict[str, Any]:
    device = tag_device(device)
    if wanted not in TRANSPORTS:
        raise PhoneError(f"Unknown transport {wanted}")
    if not device.get("usb_authorized"):
        raise PhoneError(
            f"Device {device.get('serial')} is {device.get('state')}. "
            "USB RSA / Trust This Computer, or an already-paired wireless debug session, "
            "is still required. SMS consent does not create a transport."
        )
    if wanted == "usb" and device["transport"] != "usb":
        raise PhoneError(f"Job asked for USB but device serial looks wireless: {device.get('serial')}")
    if wanted in {"wifi", "remote"} and device["transport"] == "usb":
        raise PhoneError(
            "Job asked for wifi/remote but the only visible device is USB. "
            "Run `phone transport tcpip` on USB first, then `phone transport connect`."
        )
    return device
