from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .models import ActionResult, DeviceInfo
from .safety import opaque_device_reference


class RunLog:
    def __init__(
        self,
        directory: Path,
        mode: str,
        serial: str,
        device: DeviceInfo,
        profile_id: str,
    ):
        self.directory = directory
        self.mode = mode
        self.serial = serial
        self.device = device
        self.profile_id = profile_id
        self.results: list[ActionResult] = []
        self.created = datetime.now().astimezone()

    def add(self, result: ActionResult) -> None:
        self.results.append(result)
        self.save()

    @property
    def path(self) -> Path:
        stamp = self.created.strftime("%Y%m%d-%H%M%S")
        return self.directory / f"run-{stamp}-{self.mode}.json"

    def payload(self) -> dict[str, Any]:
        return {
            "tool": "HyperOS Privacy Toolkit",
            "created": self.created.isoformat(),
            "mode": self.mode,
            "device_reference": opaque_device_reference(self.serial),
            "device": self.device.public_dict(),
            "profile": self.profile_id,
            "results": [result.to_dict() for result in self.results],
        }

    def save(self) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
        return self.path
