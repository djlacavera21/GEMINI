from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from gemini_cloner.util import ensure_dir, read_json, utc_now, write_json

SCOPES = ("media", "documents", "packages", "sms_export", "adb_backup", "ios_backup")

class ConsentError(RuntimeError):
    pass

def _now() -> datetime:
    return datetime.now(timezone.utc)

def parse_ts(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

def secret_path(root: Path) -> Path:
    return root / ".gemini-consent-secret"

def load_secret(root: Path) -> bytes:
    path = secret_path(root)
    if path.is_file():
        return path.read_bytes()
    ensure_dir(root)
    value = secrets.token_bytes(32)
    path.write_bytes(value)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return value

def jobs_dir(root: Path) -> Path:
    return ensure_dir(root / "phone-jobs")

def job_path(root: Path, job_id: str) -> Path:
    return jobs_dir(root) / f"{job_id}.json"

def sign(secret: bytes, payload: str) -> str:
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

def make_job(root: Path, *, phone: str, platform: str, serial: str, scope: list[str], operator: str, ttl_minutes: int = 15, public_base: str = "http://127.0.0.1:8787", transport: str = "usb") -> dict[str, Any]:
    unknown = [item for item in scope if item not in SCOPES]
    if unknown:
        raise ConsentError(f"Unknown scope items: {unknown}. Allowed: {SCOPES}")
    if not scope:
        raise ConsentError("Scope cannot be empty")
    if transport not in {"usb", "wifi", "remote"}:
        raise ConsentError(f"Unknown transport {transport}. Allowed: usb, wifi, remote")
    job_id = secrets.token_hex(8)
    challenge = secrets.token_urlsafe(32)
    expires = _now() + timedelta(minutes=max(2, ttl_minutes))
    session = secrets.token_hex(8)
    job = {
        "job_id": job_id,
        "created_at": utc_now(),
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "pending",
        "phone": phone,
        "platform": platform,
        "serial": serial,
        "scope": scope,
        "operator_session": session,
        "operator": operator,
        "challenge": challenge,
        "public_base": public_base.rstrip("/"),
        "approvals": [],
        "denied_reason": None,
        "transport": transport,
    }
    secret = load_secret(root)
    job["token"] = sign(secret, f"{job_id}.{challenge}.{session}")
    write_json(job_path(root, job_id), job)
    return job

def load_job(root: Path, job_id: str) -> dict[str, Any]:
    path = job_path(root, job_id)
    if not path.is_file():
        raise ConsentError(f"Unknown job {job_id}")
    return read_json(path)

def save_job(root: Path, job: dict[str, Any]) -> None:
    write_json(job_path(root, job["job_id"]), job)

def approval_url(job: dict[str, Any]) -> str:
    return f"{job['public_base']}/approve?job={job['job_id']}&token={job['token']}"

def refresh_status(job: dict[str, Any]) -> dict[str, Any]:
    if job["status"] == "pending" and _now() > parse_ts(job["expires_at"]):
        job["status"] = "expired"
    return job

def verify_token(root: Path, job_id: str, token: str) -> dict[str, Any]:
    job = refresh_status(load_job(root, job_id))
    secret = load_secret(root)
    expected = sign(secret, f"{job['job_id']}.{job['challenge']}.{job['operator_session']}")
    if not hmac.compare_digest(expected, token) or not hmac.compare_digest(job["token"], token):
        raise ConsentError("Consent token mismatch")
    if job["status"] == "expired":
        raise ConsentError("Consent link expired")
    return job

def approve_job(root: Path, job_id: str, token: str, *, method: str, client_data: dict[str, Any] | None = None, credential_id: str | None = None, note: str = "") -> dict[str, Any]:
    job = verify_token(root, job_id, token)
    if job["status"] == "approved":
        return job
    if job["status"] not in {"pending"}:
        raise ConsentError(f"Job is {job['status']}, cannot approve")
    if client_data:
        challenge = client_data.get("challenge")
        if challenge and challenge != job["challenge"]:
            raise ConsentError("Passkey challenge does not match this job")
    job["status"] = "approved"
    job["approved_at"] = utc_now()
    job["approvals"].append({"at": utc_now(), "method": method, "credential_id": credential_id, "client_data": client_data, "note": note})
    save_job(root, job)
    return job

def deny_job(root: Path, job_id: str, token: str, reason: str = "owner denied") -> dict[str, Any]:
    job = verify_token(root, job_id, token)
    job["status"] = "denied"
    job["denied_reason"] = reason
    job["denied_at"] = utc_now()
    save_job(root, job)
    return job

def require_approved(root: Path, job_id: str) -> dict[str, Any]:
    job = refresh_status(load_job(root, job_id))
    if job["status"] != "approved":
        raise ConsentError(f"Job {job_id} is {job['status']}, not approved")
    if _now() > parse_ts(job["expires_at"]) + timedelta(hours=2):
        raise ConsentError("Approved job is too old to execute")
    return job

def decode_client_data(client_data_json_b64: str) -> dict[str, Any]:
    import base64
    raw = client_data_json_b64
    pad = "=" * (-len(raw) % 4)
    return json.loads(base64.urlsafe_b64decode(raw + pad).decode("utf-8"))
