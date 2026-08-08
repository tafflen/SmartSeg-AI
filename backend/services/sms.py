"""Best-effort notification sender; mirrors ai-engine's offline-safe SMS behavior."""
from __future__ import annotations
import logging, os, threading

LOGGER = logging.getLogger(__name__)

def send_sms_async(phone: str | None, message: str) -> None:
    if not phone: return
    def send() -> None:
        try:
            if os.getenv("SMARTSEG_SMS_PROVIDER", "mock").lower() == "twilio":
                from twilio.rest import Client
                Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]).messages.create(
                    to=phone, from_=os.environ["TWILIO_FROM_PHONE"], body=message)
            else: LOGGER.info("MOCK SMS to %s: %s", phone, message)
        except Exception: LOGGER.exception("SMS failed without affecting the transaction")
    threading.Thread(target=send, name="smartseg-backend-sms", daemon=True).start()
