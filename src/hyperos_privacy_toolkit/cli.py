from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .adb import AdbClient, AdbError, find_adb, select_device
from .logging import RunLog
from .operations import ActionExecutor
from .profiles import (
    ProfileError,
    action_by_id,
    default_profiles_dir,
    load_profiles,
    select_profile,
)
from .safety import SafetyError, opaque_device_reference
from .ui import UiError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hyperos-privacy")
    parser.add_argument("--adb", help="Path to the official adb executable")
    parser.add_argument("--serial", help="ADB serial, IP:port or mDNS endpoint")
    parser.add_argument("--profile", help="Require a specific compatibility profile")
    parser.add_argument(
        "--profiles-dir", type=Path, default=default_profiles_dir(), help="Profiles directory"
    )
    parser.add_argument(
        "--log-dir", type=Path, default=Path("runtime/logs"), help="Local runtime log directory"
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("doctor", help="Detect ADB, device and compatibility profile")
    subparsers.add_parser("list-actions", help="List actions available for the selected profile")

    analyze = subparsers.add_parser("analyze", help="Read settings without changing them")
    analyze.add_argument("--action")
    analyze.add_argument("--include-experimental", action="store_true")

    apply = subparsers.add_parser("apply", help="Apply one explicitly authorized action")
    apply.add_argument("action")
    apply.add_argument("--confirm", required=True)
    apply.add_argument("--acknowledge-data-deletion", action="store_true")
    apply.add_argument("--include-experimental", action="store_true")

    restore = subparsers.add_parser("restore", help="Restore one change recorded by this tool")
    restore.add_argument("log", type=Path)
    restore.add_argument("--action", required=True)
    restore.add_argument("--confirm", required=True)
    restore.add_argument("--include-experimental", action="store_true")

    sample = subparsers.add_parser(
        "sample-filemanager-ads", help="Experimental, privacy-safe intermittent ad sampling"
    )
    sample.add_argument("--attempts", type=int, default=5)
    sample.add_argument("--output-dir", type=Path, default=Path("runtime/evidence"))
    sample.add_argument("--include-experimental", action="store_true")
    return parser


def _environment(args: argparse.Namespace):
    adb_path = find_adb(args.adb)
    discovery = AdbClient(adb_path)
    connected = select_device(discovery.list_devices(), args.serial)
    client = AdbClient(adb_path, connected.serial)
    info = client.detect_device_info(connected.transport)
    profiles = load_profiles(args.profiles_dir.resolve())
    profile = select_profile(profiles, info, args.profile)
    return adb_path, connected, client, info, profile


def _print(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        args.command = "analyze"
        args.action = None
        args.include_experimental = False

    try:
        adb_path, connected, _client, info, profile = _environment(args)
        public_environment = {
            "adb": {"found": True, "version_check": str(adb_path.name)},
            "device_reference": opaque_device_reference(connected.serial),
            "device": info.public_dict(),
            "profile": {
                "id": profile["id"],
                "name": profile["name"],
                "status": profile["status"],
            },
        }
        if args.command == "doctor":
            _print(public_environment)
            return
        if args.command == "list-actions":
            _print({
                **public_environment,
                "actions": [
                    {
                        "id": action["id"],
                        "title": action["title"],
                        "maturity": action["maturity"],
                        "writable": action.get("writable", False),
                    }
                    for action in profile.get("actions", [])
                ],
            })
            return

        run_log = RunLog(
            args.log_dir.resolve(),
            args.command,
            connected.serial,
            info,
            profile["id"],
        )
        executor = ActionExecutor(connected.serial, profile, run_log)
        try:
            if args.command == "analyze":
                actions = profile.get("actions", [])
                if args.action:
                    actions = [action_by_id(profile, args.action)]
                results = [
                    executor.analyze(action["id"], args.include_experimental).to_dict()
                    for action in actions
                    if action.get("analyzable", True)
                ]
            elif args.command == "apply":
                results = [
                    executor.apply(
                        args.action,
                        args.confirm,
                        args.acknowledge_data_deletion,
                        args.include_experimental,
                    ).to_dict()
                ]
            elif args.command == "restore":
                results = [
                    executor.restore(
                        args.log.resolve(),
                        args.action,
                        args.confirm,
                        args.include_experimental,
                    ).to_dict()
                ]
            elif args.command == "sample-filemanager-ads":
                if not args.include_experimental:
                    raise ProfileError("This command is experimental; pass --include-experimental")
                if not 1 <= args.attempts <= 30:
                    raise ProfileError("--attempts must be between 1 and 30")
                results = [
                    executor.sample_file_manager_ads(
                        args.attempts, args.output_dir.resolve()
                    ).to_dict()
                ]
            else:
                raise ProfileError(f"Unsupported command: {args.command}")
        finally:
            executor.press_home()
        _print({**public_environment, "log": str(run_log.path), "results": results})
    except (AdbError, ProfileError, SafetyError, UiError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
