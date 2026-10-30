from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConnectedDevice:
    serial: str
    state: str
    properties: dict[str, str]
    transport: str


@dataclass(frozen=True)
class DeviceInfo:
    model: str
    device: str
    android: str
    miui: str
    hyperos: str
    build: str
    region: str
    locale: str
    current_user: str
    transport: str

    def public_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class ActionResult:
    action_id: str
    title: str
    status: str
    initial: Any = None
    final: Any = None
    changed: bool = False
    verified: bool = False
    restorable: bool = False
    note: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
