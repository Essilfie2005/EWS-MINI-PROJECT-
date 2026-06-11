"""
Africa's Talking SMS Service.

Real integration with sandbox mode by default.
Falls back to logging when no API key is configured.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_at_client():
    """
    Initialise and return the Africa's Talking SMS client.
    Returns None if no API key is configured (fallback to logging).
    """
    settings = get_settings()
    if not settings.AT_API_KEY:
        logger.info("No AT_API_KEY configured – SMS will be logged only (mock mode).")
        return None

    try:
        import africastalking
        africastalking.initialize(
            username=settings.AT_USERNAME,
            api_key=settings.AT_API_KEY,
        )
        return africastalking.SMS
    except ImportError:
        logger.warning("africastalking package not installed – SMS will be logged only.")
        return None
    except Exception as e:
        logger.error("Failed to initialise Africa's Talking: %s", e)
        return None


def send_sms(
    phone_number: str,
    message: str,
    sender_id: Optional[str] = None,
) -> dict:
    """
    Send an SMS via Africa's Talking.

    Parameters
    ----------
    phone_number : str
        Recipient phone number in international format (e.g. +233XXXXXXXXX).
    message : str
        SMS body text (max 160 chars recommended).
    sender_id : str, optional
        Sender ID override.

    Returns
    -------
    dict with keys: success, message, sms_id, raw_response
    """
    settings = get_settings()
    sender = sender_id or settings.AT_SENDER_ID or None

    sms_client = _get_at_client()

    if sms_client is None:
        # ── Mock / log-only mode ──────────────────────────────────────────
        logger.info(
            "[SMS-MOCK] To: %s | From: %s | Message: %s",
            phone_number, sender or "DEFAULT", message,
        )
        return {
            "success": True,
            "message": f"SMS logged (mock mode) to {phone_number}",
            "sms_id": "mock-no-api-key",
            "raw_response": None,
        }

    try:
        # ── Real Africa's Talking API call ────────────────────────────────
        kwargs = {
            "message": message,
            "recipients": [phone_number],
        }
        if sender:
            kwargs["sender_id"] = sender

        response = sms_client.send(**kwargs)

        logger.info("AT SMS response: %s", response)

        # Parse response
        sms_data = response.get("SMSMessageData", {})
        recipients = sms_data.get("Recipients", [])

        if recipients:
            first = recipients[0]
            status_code = first.get("statusCode", 0)
            return {
                "success": status_code == 101,  # 101 = Sent
                "message": first.get("status", "Unknown"),
                "sms_id": first.get("messageId", ""),
                "raw_response": response,
            }
        else:
            return {
                "success": False,
                "message": sms_data.get("Message", "No recipients in response"),
                "sms_id": None,
                "raw_response": response,
            }

    except Exception as e:
        logger.error("SMS send failed: %s", e, exc_info=True)
        return {
            "success": False,
            "message": f"SMS send error: {str(e)}",
            "sms_id": None,
            "raw_response": None,
        }


def build_alert_message(
    student_anon_id: str,
    risk_score: float,
    risk_band: str,
    top_factors: list[str],
) -> str:
    """
    Build a formatted SMS alert message for a flagged student.

    Parameters
    ----------
    student_anon_id : str – anonymised student ID (will be truncated for SMS)
    risk_score : float – 0-1 probability
    risk_band : str – LOW / MEDIUM / HIGH
    top_factors : list[str] – human-readable risk factor strings

    Returns
    -------
    str – SMS message body
    """
    truncated_id = student_anon_id[:8]
    factors_text = "; ".join(top_factors[:3]) if top_factors else "Multiple factors"

    msg = (
        f"[DROPOUT ALERT] Student {truncated_id}\n"
        f"Risk: {risk_band} ({risk_score:.0%})\n"
        f"Factors: {factors_text}\n"
        f"Action needed. Check the Early Warning Dashboard."
    )

    # Ensure within SMS limits (keep under 320 chars for multi-part)
    if len(msg) > 320:
        msg = msg[:317] + "..."

    return msg


def send_alert_sms(
    phone_number: str,
    student_anon_id: str,
    risk_score: float,
    risk_band: str,
    top_factors: list[str],
) -> dict:
    """Convenience: build message and send in one call."""
    message = build_alert_message(student_anon_id, risk_score, risk_band, top_factors)
    return send_sms(phone_number, message)
