"""
Twilio WhatsApp Service.

Integration for sending WhatsApp messages via Twilio Sandbox.
Falls back to logging if credentials are not configured.
"""

import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)

def _get_twilio_client():
    settings = get_settings()
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.info("Twilio credentials not configured – WhatsApp will be logged only.")
        return None

    try:
        from twilio.rest import Client
        return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    except ImportError:
        logger.warning("twilio package not installed – WhatsApp will be logged only.")
        return None
    except Exception as e:
        logger.error("Failed to initialise Twilio Client: %s", e)
        return None

def send_whatsapp(
    phone_number: str,
    message: str,
) -> dict:
    """
    Send a WhatsApp message via Twilio.
    """
    settings = get_settings()
    
    # Ensure phone number is formatted for WhatsApp (requires 'whatsapp:' prefix)
    if not phone_number.startswith("whatsapp:"):
        # If it doesn't have the prefix, add it. (Assumes it's already in E.164 format like +1234567890)
        formatted_phone = f"whatsapp:{phone_number}"
    else:
        formatted_phone = phone_number

    from_number = settings.TWILIO_WHATSAPP_NUMBER
    if not from_number:
        from_number = "whatsapp:+14155238886"  # Default Twilio Sandbox Number
    elif not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"

    client = _get_twilio_client()

    if client is None:
        # Mock mode
        logger.info(
            "[WHATSAPP-MOCK] To: %s | From: %s | Message: %s",
            formatted_phone, from_number, message,
        )
        return {
            "success": True,
            "message": f"WhatsApp logged (mock mode) to {formatted_phone}",
            "whatsapp_id": "mock-no-api-key",
            "raw_response": None,
        }

    try:
        message_obj = client.messages.create(
            from_=from_number,
            body=message,
            to=formatted_phone
        )
        logger.info("Twilio WhatsApp response SID: %s", message_obj.sid)

        return {
            "success": message_obj.status not in ['failed', 'undelivered'],
            "message": message_obj.status,
            "whatsapp_id": message_obj.sid,
            "raw_response": {"sid": message_obj.sid, "status": message_obj.status},
        }

    except Exception as e:
        logger.error("WhatsApp send failed: %s", e, exc_info=True)
        return {
            "success": False,
            "message": f"WhatsApp send error: {str(e)}",
            "whatsapp_id": None,
            "raw_response": None,
        }
