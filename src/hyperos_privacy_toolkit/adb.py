from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Iterable

from .models import ConnectedDevice, DeviceInfo
from .safety import transport_kind


class AdbError(RuntimeError):
    pass


def find_adb(explicit: str | None = None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if candidate.is_file():
            return candidate
        raise AdbError(f"ADB was not found at: {candidate}")

    found = shutil.which("adb") or shutil.which("adb.exe")
    if found:
        return Path(found).resolve()

    candidates: list[Path] = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    program_files = os.environ.get("ProgramFiles")
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Android/Sdk/platform-tools/adb.exe")
    if program_files:
        candidates.append(Path(program_files) / "Android/Android Studio/platform-tools/adb.exe")
    if program_files_x86:
        candidates.append(Path(program_files_x86) / "Android/android-sdk/platform-tools/adb.exe")
    candidates.append(Path("C:/Android/platform-tools/adb.exe"))

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise AdbError(
        "Android SDK Platform-Tools were not found. Install the official package "
        "or pass --adb PATH."
    )


def parse_devices(output: str) -> list[ConnectedDevice]:
    devices: list[ConnectedDevice] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices attached") or line.startswith("*"):
            continue
        parts = re.split(r"\s+", line)
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        properties: dict[str, str] = {}
        for item in parts[2:]:
            if ":" in item:
                key, value = item.split(":", 1)
                properties[key] = value
        devices.append(
            ConnectedDevice(
                serial=serial,
                state=state,
                properties=properties,
                transport=transport_kind(serial),
            )
        )
    return devices


def _identity_key(device: ConnectedDevice) -> tuple[str, str, str]:
    return (
        device.properties.get("product", ""),
        device.properties.get("model", ""),
        device.properties.get("device", ""),
    )


def select_device(
    devices: Iterable[ConnectedDevice], requested_serial: str | None = None
) -> ConnectedDevice:
    all_devices = list(devices)
    if requested_serial:
        for device in all_devices:
            if device.serial == requested_serial:
                if device.state != "device":
                    raise AdbError(f"Requested device is {device.state}, not ready")
                return device
        raise AdbError("The requested ADB device is not connected")

    ready = [device for device in all_devices if device.state == "device"]
    if not ready:
        states = ", ".join(sorted({device.state for device in all_devices})) or "none"
        raise AdbError(f"No ready ADB device found (states: {states})")
    if len(ready) == 1:
        return ready[0]

    groups: dict[tuple[str, str, str], list[ConnectedDevice]] = {}
    for device in ready:
        groups.setdefault(_identity_key(device), []).append(device)
    non_empty_groups = {key: value for key, value in groups.items() if any(key)}
    if len(non_empty_groups) == 1 and sum(len(v) for v in non_empty_groups.values()) == len(ready):
        same_phone = next(iter(non_empty_groups.values()))
        # Prefer USB, then the stable mDNS name, then an IP:port endpoint.
        return sorted(
            same_phone,
            key=lambda item: (
                0 if item.transport == "usb" else 1,
                0 if "_adb-tls-connect._tcp" in item.serial else 1,
                item.serial,
            ),
        )[0]
    raise AdbError("Multiple distinct ADB devices are connected; pass --serial explicitly")


def parse_enabled_code(dumpsys_output: str, user_id: str = "0") -> int | None:
    pattern = rf"User\s+{re.escape(user_id)}:.*?enabled=(\d+)"
    match = re.search(pattern, dumpsys_output)
    return int(match.group(1)) if match else None


def enabled_state_name(code: int | None) -> str:
    return {
        0: "DEFAULT",
        1: "ENABLED",
        2: "DISABLED",
        3: "DISABLED_USER",
        4: "DISABLED_UNTIL_USED",
    }.get(code, "UNKNOWN")


class AdbClient:
    def __init__(self, adb_path: Path, serial: str | None = None, timeout: int = 25):
        self.adb_path = adb_path
        self.serial = serial
        self.timeout = timeout

    def run(
        self,
        arguments: list[str],
        *,
        check: bool = True,
        serial: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command = [str(self.adb_path)]
        if serial and self.serial:
            command.extend(["-s", self.serial])
        command.extend(arguments)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout,
            check=False,
        )
        if check and completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise AdbError(f"ADB command failed ({completed.returncode}): {detail}")
        return completed

    def list_devices(self) -> list[ConnectedDevice]:
        return parse_devices(self.run(["devices", "-l"], serial=False).stdout)

    def shell(self, arguments: list[str], *, check: bool = True) -> str:
        return self.run(["shell", *arguments], check=check).stdout.strip()

    def getprop(self, name: str) -> str:
        return self.shell(["getprop", name], check=False).strip()

    def detect_device_info(self, transport: str) -> DeviceInfo:
        user = self.shell(["cmd", "activity", "get-current-user"], check=False)
        if not user.isdigit():
            user = "0"
        return DeviceInfo(
            model=self.getprop("ro.product.model"),
            device=self.getprop("ro.product.device"),
            android=self.getprop("ro.build.version.release"),
            miui=self.getprop("ro.miui.ui.version.name"),
            hyperos=(
                self.getprop("ro.mi.os.version.incremental")
                or self.getprop("ro.mi.os.version.name")
                or self.getprop("ro.system.build.version.incremental")
            ),
            build=self.getprop("ro.build.display.id"),
            region=self.getprop("ro.miui.region"),
            locale=self.getprop("persist.sys.locale"),
            current_user=user,
            transport=transport,
        )
