from __future__ import annotations

import os
from typing import Any

import httpx


class SmsError(RuntimeError):
    pass


def configured() -> bool:
    return bool(os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN") and os.environ.get("TWILIO_FROM"))


def send_approval_sms(to_number: str, body: str) -> dict[str, Any]:
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.environ.get("TWILIO_FROM", "").strip()
    if not (sid and token and from_number):
        raise SmsError(
            "SMS not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM, "
            "or send the printed approval link yourself."
        )
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            url,
            auth=(sid, token),
            data={"From": from_number, "To": to_number, "Body": body},
        )
    if response.status_code >= 400:
        raise SmsError(f"Twilio {response.status_code}: {response.text[:300]}")
    payload = response.json()
    return {"sid": payload.get("sid"), "status": payload.get("status"), "to": to_number}
