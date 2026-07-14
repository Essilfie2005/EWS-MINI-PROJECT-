"""
Africa's Talking SMS Service
=============================
Sends counsellor alert SMS via Africa's Talking API.

Configuration (set in .env):
  AT_API_KEY   - Africa's Talking API key (or "sandbox" for testing)
  AT_USERNAME  - Africa's Talking username (or "sandbox")
  AT_SENDER_ID - Short code / sender ID (optional)

When AT_API_KEY is not set, alerts are logged to console only (graceful fallback).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# These will be read from environment at call time so .env changes are picked up
_AT_AVAILABLE: Optional[bool] = None


def _check_at_available() -> bool:
    global _AT_AVAILABLE
    if _AT_AVAILABLE is None:
        try:
            import africastalking  # noqa: F401
            _AT_AVAILABLE = True
        except ImportError:
            _AT_AVAILABLE = False
    return _AT_AVAILABLE


def send_sms(phone_numbers: list[str], message: str) -> dict:
    """
    Send an SMS to one or more phone numbers via Africa's Talking.

    Parameters
    ----------
    phone_numbers : list of E.164 strings e.g. ['+233241234567']
    message       : SMS body (max 160 chars for single part)

    Returns
    -------
    dict with status, recipients, message
    """
    api_key  = os.getenv("AT_API_KEY", "")
    username = os.getenv("AT_USERNAME", "sandbox")
    sender   = os.getenv("AT_SENDER_ID", None)

    if not api_key:
        logger.warning(
            "AT_API_KEY not set — SMS alert logged only (no real SMS sent). "
            "Set AT_API_KEY in your .env to enable live SMS.\n"
            "  Recipients: %s\n  Message: %s",
            phone_numbers, message
        )
        return {
            "status": "logged_only",
            "message": message,
            "recipients": phone_numbers,
            "note": "Set AT_API_KEY in .env to enable real SMS delivery.",
        }

    if not _check_at_available():
        logger.error("africastalking package not installed. Run: pip install africastalking")
        return {
            "status": "error",
            "message": "africastalking package not installed",
            "recipients": [],
        }

    try:
        import africastalking
        africastalking.initialize(username, api_key)
        sms = africastalking.SMS

        kwargs: dict = {"message": message, "recipients": phone_numbers}
        if sender:
            kwargs["sender_id"] = sender

        response = sms.send(**kwargs)
        logger.info("Africa's Talking SMS sent: %s", response)

        recipients = []
        for r in response.get("SMSMessageData", {}).get("Recipients", []):
            recipients.append({
                "number": r.get("number"),
                "status": r.get("status"),
                "cost": r.get("cost"),
                "message_id": r.get("messageId"),
            })

        return {
            "status": "sent",
            "message": message,
            "recipients": recipients,
            "raw": response,
        }

    except Exception as exc:
        logger.error("Africa's Talking SMS failed: %s", exc)
        return {"status": "error", "message": str(exc), "recipients": []}


def build_counsellor_alert(student_code: str, risk_band: str, top_factors: list[str]) -> str:
    """
    Build a concise SMS alert for a counsellor.
    Keeps message under 160 characters for single-part SMS.
    """
    factors_str = "; ".join(top_factors[:2]) if top_factors else "See dashboard"
    msg = (
        f"EWS ALERT: Student {student_code} flagged {risk_band}. "
        f"Key factors: {factors_str}. "
        f"Please contact within 5 days."
    )
    # Truncate to 160 chars if needed
    if len(msg) > 160:
        msg = msg[:157] + "..."
    return msg
