from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from typing import Any


class UiError(RuntimeError):
    pass


class UiDriver:
    def __init__(self, serial: str):
        try:
            import uiautomator2 as u2
        except ImportError as exc:
            raise UiError(
                "uiautomator2 is required for UI actions. Run: pip install -r requirements.txt"
            ) from exc
        self.device = u2.connect(serial)

    def root(self) -> ET.Element:
        return ET.fromstring(self.device.dump_hierarchy())

    @staticmethod
    def center(bounds: str) -> tuple[int, int]:
        parts = bounds.replace("][", ",").strip("[]").split(",")
        if len(parts) != 4:
            raise UiError(f"Invalid UI bounds: {bounds}")
        x1, y1, x2, y2 = map(int, parts)
        return (x1 + x2) // 2, (y1 + y2) // 2

    @staticmethod
    def area(bounds: str) -> int:
        try:
            x1, y1, x2, y2 = map(
                int, bounds.replace("][", ",").strip("[]").split(",")
            )
            return max(0, x2 - x1) * max(0, y2 - y1)
        except (TypeError, ValueError):
            return 10**12

    def find_switch(self, labels: list[str]) -> ET.Element | None:
        root = self.root()
        parents = {child: parent for parent in root.iter() for child in parent}
        for label in labels:
            candidates = [
                node
                for node in root.iter("node")
                if node.attrib.get("text") == label
                or node.attrib.get("content-desc") == label
            ]
            for label_node in candidates:
                cursor: ET.Element | None = label_node
                while cursor is not None:
                    switches = [
                        node
                        for node in cursor.iter("node")
                        if node.attrib.get("checkable") == "true"
                        and (
                            "Switch" in node.attrib.get("class", "")
                            or "CheckBox" in node.attrib.get("class", "")
                        )
                    ]
                    if switches:
                        switches.sort(key=lambda node: self.area(node.attrib.get("bounds", "")))
                        return switches[0]
                    cursor = parents.get(cursor)
        return None

    def click_node(self, node: ET.Element) -> None:
        self.device.click(*self.center(node.attrib["bounds"]))

    def click_text(self, labels: list[str], class_name: str | None = None) -> str:
        for label in labels:
            selector: dict[str, Any] = {"text": label}
            if class_name:
                selector["className"] = class_name
            target = self.device(**selector)
            if target.exists:
                target.click()
                return label
        raise UiError(f"None of these labels was found: {labels}")

    def scroll_to_text(self, labels: list[str], attempts: int = 6) -> str:
        for label in labels:
            if self.device(text=label).exists:
                return label
        scrollable = self.device(scrollable=True)
        if scrollable.exists:
            for label in labels:
                try:
                    if scrollable.scroll.to(text=label):
                        return label
                except Exception:
                    pass
        width, height = self.device.window_size()
        for _ in range(attempts):
            self.device.swipe(width // 2, int(height * 0.80), width // 2, int(height * 0.35), 0.3)
            time.sleep(0.5)
            for label in labels:
                if self.device(text=label).exists:
                    return label
        raise UiError(f"Could not find after scrolling: {labels}")

    def execute_route(self, route: list[dict[str, Any]]) -> None:
        for step in route:
            operation = step["op"]
            if operation == "launch":
                self.device.app_start(step["package"], stop=True, wait=True)
            elif operation == "start_action":
                self.device.shell(["am", "start", "-a", step["action"]])
            elif operation == "app_details":
                self.device.shell([
                    "am", "start", "-a", "android.settings.APPLICATION_DETAILS_SETTINGS",
                    "-d", f"package:{step['package']}",
                ])
            elif operation == "click_id":
                target = self.device(resourceId=step["id"])
                if not target.exists:
                    raise UiError(f"UI resource was not found: {step['id']}")
                target.click()
            elif operation == "click_text":
                self.click_text(step["labels"], step.get("class"))
            elif operation == "scroll_to_text":
                self.scroll_to_text(step["labels"], step.get("attempts", 6))
            elif operation == "set_text":
                target = self.device(className=step.get("class", "android.widget.EditText"))
                if not target.exists:
                    raise UiError("Text input was not found")
                target.set_text(step["value"])
            elif operation == "wait":
                time.sleep(float(step.get("seconds", 1)))
            else:
                raise UiError(f"Unsupported route operation: {operation}")
            if operation not in {"wait", "scroll_to_text"}:
                time.sleep(float(step.get("after", 0.8)))

    def read_control(self, resource_id: str) -> dict[str, bool]:
        control = self.device(resourceId=resource_id)
        if not control.exists:
            raise UiError(f"Control was not found: {resource_id}")
        info = control.info
        return {
            "checked": bool(info.get("checked")),
            "enabled": bool(info.get("enabled")),
            "clickable": bool(info.get("clickable")),
        }

    def wait_enabled(self, resource_id: str, timeout: float) -> Any:
        deadline = time.time() + timeout
        target = self.device(resourceId=resource_id)
        while time.time() < deadline:
            if target.exists and target.info.get("enabled"):
                return target
            time.sleep(0.5)
        raise UiError(f"Control did not become enabled: {resource_id}")
