"""Swappable, fire-and-forget SMS notifications."""
from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod

import config

LOGGER = logging.getLogger(__name__)


class SMSProvider(ABC):
    @abstractmethod
    def send(self, phone: str, message: str) -> None:
        """Send one SMS or raise an exception that the caller can safely log."""


class MockSMSProvider(SMSProvider):
    def send(self, phone: str, message: str) -> None:
        LOGGER.info("MOCK SMS to %s: %s", phone, message)


class TwilioSMSProvider(SMSProvider):
    def __init__(self) -> None:
        from twilio.rest import Client
        if not all([config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN, config.TWILIO_FROM_PHONE]):
            raise ValueError("Twilio credentials and sender phone are required")
        self.client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

    def send(self, phone: str, message: str) -> None:
        self.client.messages.create(to=phone, from_=config.TWILIO_FROM_PHONE, body=message)


def build_provider() -> SMSProvider:
    return TwilioSMSProvider() if config.SMS_PROVIDER == "twilio" else MockSMSProvider()


def send_async(provider: SMSProvider, phone: str | None, message: str) -> None:
    if not phone:
        return
    def _send() -> None:
        try:
            provider.send(phone, message)
        except Exception:
            LOGGER.exception("SMS delivery failed; processing continues")
    threading.Thread(target=_send, name="smartseg-sms", daemon=True).start()
