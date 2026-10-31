from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .models import DeviceInfo


class ProfileError(RuntimeError):
    pass


def default_profiles_dir() -> Path:
    # PyInstaller extracts bundled data to _MEIPASS. Local editable installs
    # continue to resolve profiles from the repository root.
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "profiles"
    return Path(__file__).resolve().parents[2] / "profiles


def load_profiles(directory: Path) -> list[dict[str, Any]]:
    if not directory.is_dir():
        raise ProfileError(f"Profiles directory not found: {directory}")
    profiles = []
    for path in sorted(directory.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            profile = json.load(handle)
        profile["_path"] = str(path)
        profiles.append(profile)
    if not profiles:
        raise ProfileError(f"No profiles found in: {directory}")
    return profiles


def _matches(profile: dict[str, Any], device: DeviceInfo) -> bool:
    match = profile.get("match", {})
    if match.get("generic"):
        return True
    if match.get("devices") and device.device not in match["devices"]:
        return False
    if match.get("models") and device.model not in match["models"]:
        return False
    if match.get("hyperos_prefixes") and not any(
        device.hyperos.startswith(prefix) for prefix in match["hyperos_prefixes"]
    ):
        return False
    if match.get("locales") and device.locale not in match["locales"]:
        return False
    if match.get("regions") and device.region not in match["regions"]:
        return False
    return True


def select_profile(
    profiles: list[dict[str, Any]],
    device: DeviceInfo,
    requested_id: str | None = None,
) -> dict[str, Any]:
    if requested_id:
        for profile in profiles:
            if profile.get("id") == requested_id:
                if not _matches(profile, device):
                    raise ProfileError(
                        f"Profile {requested_id} does not match the connected device"
                    )
                return profile
        raise ProfileError(f"Unknown profile: {requested_id}")

    matches = [profile for profile in profiles if _matches(profile, device)]
    specific = [profile for profile in matches if not profile.get("match", {}).get("generic")]
    if specific:
        return sorted(specific, key=lambda item: item.get("priority", 0), reverse=True)[0]
    generic = [profile for profile in matches if profile.get("match", {}).get("generic")]
    if generic:
        return generic[0]
    raise ProfileError("No compatible profile was found")


def action_by_id(profile: dict[str, Any], action_id: str) -> dict[str, Any]:
    for action in profile.get("actions", []):
        if action.get("id") == action_id:
            return action
    raise ProfileError(f"Action {action_id!r} is not available in profile {profile.get('id')}")
