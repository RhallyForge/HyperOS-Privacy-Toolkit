from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any

from .logging import RunLog
from .models import ActionResult
from .profiles import ProfileError, action_by_id
from .safety import (
    require_confirmation,
    require_data_deletion_acknowledgement,
)
from .ui import UiDriver, UiError


class ActionExecutor:
    def __init__(self, serial: str, profile: dict[str, Any], run_log: RunLog):
        self.serial = serial
        self.profile = profile
        self.run_log = run_log
        self.ui = UiDriver(serial)

    def _ensure_maturity(self, action: dict[str, Any], include_experimental: bool) -> None:
        if action.get("maturity") == "experimental" and not include_experimental:
            raise ProfileError(
                f"Action {action['id']} is experimental. Re-run with --include-experimental."
            )

    def analyze(self, action_id: str, include_experimental: bool = False) -> ActionResult:
        action = action_by_id(self.profile, action_id)
        self._ensure_maturity(action, include_experimental)
        try:
            if action["kind"] == "network-audit":
                return self._analyze_network(action)
            self.ui.execute_route(action["route"])
            switch = self.ui.find_switch(action["labels"])
            if switch is None:
                raise UiError("The expected switch was not found")
            checked = switch.attrib.get("checked") == "true"
            result = ActionResult(
                action_id=action_id,
                title=action["title"],
                status="analyzed",
                initial=checked,
                final=checked,
                verified=True,
                restorable=False,
                note="Read-only analysis; no setting was changed.",
            )
        except Exception as exc:
            result = ActionResult(
                action_id=action_id,
                title=action["title"],
                status="unsupported-or-failed",
                verified=False,
                note=str(exc),
            )
        self.run_log.add(result)
        return result

    def _analyze_network(self, action: dict[str, Any]) -> ActionResult:
        self.ui.execute_route(action["route"])
        state = {
            name: self.ui.read_control(resource_id)
            for name, resource_id in action["controls"].items()
        }
        wifi_blocked = not state["wifi"]["enabled"]
        result = ActionResult(
            action_id=action["id"],
            title=action["title"],
            status="blocked-by-hyperos" if wifi_blocked else "controls-available",
            initial=state,
            final=state,
            verified=True,
            restorable=False,
            note=(
                "Wi-Fi control is present but disabled by HyperOS; no partial block was applied."
                if wifi_blocked
                else "All controls are readable. This action remains analysis-only."
            ),
        )
        self.run_log.add(result)
        return result

    def apply(
        self,
        action_id: str,
        confirmation: str | None,
        acknowledge_data_deletion: bool,
        include_experimental: bool = False,
    ) -> ActionResult:
        action = action_by_id(self.profile, action_id)
        self._ensure_maturity(action, include_experimental)
        if not action.get("writable", False):
            raise ProfileError(f"Action {action_id} is analysis-only")
        require_confirmation(action_id, confirmation)
        if action.get("risk") == "server-data-deletion":
            require_data_deletion_acknowledgement(acknowledge_data_deletion)

        try:
            self.ui.execute_route(action["route"])
            switch = self.ui.find_switch(action["labels"])
            if switch is None:
                raise UiError("The expected switch was not found")
            initial = switch.attrib.get("checked") == "true"
            if not initial:
                result = ActionResult(
                    action_id=action_id,
                    title=action["title"],
                    status="already-disabled",
                    initial=False,
                    final=False,
                    verified=True,
                    restorable=False,
                    note="No touch was performed.",
                )
                self.run_log.add(result)
                return result

            self.ui.click_node(switch)
            confirmation_spec = action.get("confirmation")
            if confirmation_spec:
                self._handle_confirmation(confirmation_spec)
            else:
                time.sleep(1)

            after = self.ui.find_switch(action["labels"])
            final = None if after is None else after.attrib.get("checked") == "true"
            persistence = None
            if final is False and action.get("verify_reopen"):
                self.ui.device.app_stop(action["verify_reopen"])
                time.sleep(1)
                self.ui.execute_route(action["route"])
                reopened = self.ui.find_switch(action["labels"])
                persistence = None if reopened is None else reopened.attrib.get("checked") == "true"
                final = persistence

            changed = final is False
            result = ActionResult(
                action_id=action_id,
                title=action["title"],
                status="changed" if changed else "failed",
                initial=True,
                final=final,
                changed=changed,
                verified=changed,
                restorable=changed and action.get("restore_mode") == "automatic",
                note=(
                    "Setting changed and verified."
                    if changed
                    else "The final UI state did not match the requested state."
                ),
                details={"persistence_checked": persistence is not None},
            )
        except Exception as exc:
            result = ActionResult(
                action_id=action_id,
                title=action["title"],
                status="failed",
                verified=False,
                note=str(exc),
            )
        self.run_log.add(result)
        return result

    def _handle_confirmation(self, spec: dict[str, Any]) -> None:
        if spec.get("type") == "countdown-button":
            target = self.ui.wait_enabled(spec["resource_id"], float(spec.get("timeout", 15)))
            target.click()
            time.sleep(float(spec.get("after", 3)))
            return
        if spec.get("type") == "conditional-text":
            titles = spec.get("titles", [])
            if any(self.ui.device(text=title).exists for title in titles):
                self.ui.click_text(spec["accept_labels"])
                time.sleep(float(spec.get("after", 1)))
            return
        raise UiError(f"Unsupported confirmation type: {spec.get('type')}")

    def restore(
        self,
        source_log: Path,
        action_id: str,
        confirmation: str | None,
        include_experimental: bool = False,
    ) -> ActionResult:
        action = action_by_id(self.profile, action_id)
        self._ensure_maturity(action, include_experimental)
        require_confirmation(action_id, confirmation)
        source = json.loads(source_log.read_text(encoding="utf-8"))
        records = [
            item
            for item in source.get("results", [])
            if item.get("action_id") == action_id
            and item.get("status") == "changed"
            and item.get("initial") is True
            and item.get("final") is False
        ]
        if not records:
            raise ProfileError("The source log does not contain a restorable change for this action")
        if action.get("restore_mode") != "automatic":
            result = ActionResult(
                action_id=action_id,
                title=action["title"],
                status="manual-restore-required",
                verified=False,
                note=action.get("manual_restore", "Use the official UI to restore this setting."),
            )
            self.run_log.add(result)
            return result

        try:
            self.ui.execute_route(action["route"])
            switch = self.ui.find_switch(action["labels"])
            if switch is None:
                raise UiError("The switch could not be found during restore")
            initial = switch.attrib.get("checked") == "true"
            if not initial:
                self.ui.click_node(switch)
                time.sleep(1)
            after = self.ui.find_switch(action["labels"])
            final = None if after is None else after.attrib.get("checked") == "true"
            result = ActionResult(
                action_id=action_id,
                title=action["title"],
                status="restored" if final is True else "restore-failed",
                initial=initial,
                final=final,
                changed=not initial and final is True,
                verified=final is True,
                note="Restored to the state recorded before this tool changed it.",
            )
        except Exception as exc:
            result = ActionResult(
                action_id=action_id,
                title=action["title"],
                status="restore-failed",
                verified=False,
                note=str(exc),
            )
        self.run_log.add(result)
        return result

    def press_home(self) -> None:
        self.ui.device.press("home")

    def sample_file_manager_ads(
        self, attempts: int, output_directory: Path
    ) -> ActionResult:
        config = self.profile.get("file_manager_ad_sampling")
        if not config:
            raise ProfileError("File Manager ad sampling is not available in this profile")
        output_directory.mkdir(parents=True, exist_ok=True)
        samples = []
        ad_activity = config["ad_activity"]
        package = config["package"]
        screenshot = None
        observed = False
        for attempt in range(1, attempts + 1):
            self.ui.device.app_start(package, stop=True, wait=True)
            time.sleep(float(config.get("wait_seconds", 5)))
            current = self.ui.device.app_current()
            samples.append({"attempt": attempt, "activity": current.get("activity")})
            if current.get("activity") == ad_activity:
                screenshot = output_directory / "filemanager-ad-observed.png"
                self.ui.device.screenshot(str(screenshot))
                observed = True
                break
            self.ui.device.press("home")
            time.sleep(1)
        if not observed:
            self.ui.device.app_start(package, stop=True, wait=True)
            time.sleep(float(config.get("wait_seconds", 5)))
            current = self.ui.device.app_current()
            if current.get("activity") == ad_activity:
                screenshot = output_directory / "filemanager-ad-observed.png"
                self.ui.device.screenshot(str(screenshot))
                observed = True
            else:
                screenshot = output_directory / "filemanager-no-ad-sample.png"
                image = self.ui.device.screenshot(format="pillow")
                image.crop((0, 0, image.width, min(360, image.height))).save(screenshot)
        result = ActionResult(
            action_id="filemanager-ad-sample",
            title="File Manager intermittent ad sample",
            status="ad-observed" if observed else "not-observed-in-sample",
            verified=True,
            note=(
                "The configured advertising activity was observed."
                if observed
                else "No ad was observed; this does not prove permanent removal."
            ),
            details={
                "attempts": len(samples),
                "samples": samples,
                "screenshot": screenshot.name if screenshot else None,
            },
        )
        self.run_log.add(result)
        return result
