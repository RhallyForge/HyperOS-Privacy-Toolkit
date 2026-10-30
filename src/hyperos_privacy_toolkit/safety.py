from __future__ import annotations

import hashlib
import re


class SafetyError(RuntimeError):
    pass


def require_confirmation(action_id: str, provided: str | None) -> None:
    if provided != action_id:
        raise SafetyError(
            f"Refusing to modify the device. Re-run with --confirm {action_id}."
        )


def require_data_deletion_acknowledgement(acknowledged: bool) -> None:
    if not acknowledged:
        raise SafetyError(
            "This action displays a Xiaomi warning about server-side data deletion. "
            "Re-run with --acknowledge-data-deletion after reading the warning."
        )


def transport_kind(serial: str) -> str:
    if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}:\d+$", serial):
        return "wireless"
    if "_adb-tls-connect._tcp" in serial:
        return "wireless"
    return "usb"


def opaque_device_reference(serial: str) -> str:
    """Return a non-reversible local reference without leaking a serial or IP."""
    digest = hashlib.sha256(serial.encode("utf-8")).hexdigest()[:10]
    return f"{transport_kind(serial)}-{digest}"


def assert_no_obvious_secret(text: str) -> None:
    patterns = {
        "IPv4 address": r"\b(?:\d{1,3}\.){3}\d{1,3}:\d+\b",
        "ADB pairing code": r"\b\d{6}\b",
        "private key": r"-----BEGIN " + r"(?:RSA |OPENSSH )?PRIVATE KEY-----",
        "GitHub token": r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b",
    }
    for label, pattern in patterns.items():
        if re.search(pattern, text):
            raise SafetyError(f"Potential {label} found in publishable content")
