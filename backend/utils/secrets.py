"""Helpers to encrypt/decrypt sensitive values using Fernet."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode

from cryptography.fernet import Fernet

from backend.config.settings import settings


def _get_cipher() -> Fernet:
    if not settings.encryption_key:
        raise ValueError("ENCRYPTION_KEY must be set for secret encryption")
    key_bytes = urlsafe_b64decode(settings.encryption_key.encode("utf-8"))
    return Fernet(urlsafe_b64encode(key_bytes))


def encrypt_secret(value: str) -> str:
    cipher = _get_cipher()
    return cipher.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    cipher = _get_cipher()
    return cipher.decrypt(value.encode("utf-8")).decode("utf-8")








