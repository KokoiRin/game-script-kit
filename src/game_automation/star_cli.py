"""star — 游戏脚本自动化统一命令行入口。"""

from __future__ import annotations

import argparse
import sys

from game_automation.adapters.dry_run import DryRunInputDevice, DryRunPixelColorReader
from game_automation.domain import Color
from game_automation.engine.script_requirements import inspect_script_requirements
from game_automation.engine.runner import ScriptRunner
from game_automation.scripts_manager import DEFAULT_SCRIPT_CATALOG
from game_automation.scripts_manager.catalog import ScriptNotFoundError


def _run_list() -> int:
    """列出所有可用脚本。"""
    for name in DEFAULT_SCRIPT_CATALOG.list_names():
        print(name)
    return 0


def _run_script(args: argparse.Namespace) -> int:
    """按名称运行脚本。"""
    try:
        script = DEFAULT_SCRIPT_CATALOG.get(args.name)
    except ScriptNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    requirements = inspect_script_requirements(script)
    if args.dry_run:
        color_reader = None
        if requirements.needs_color_reader:
            try:
                color_reader = DryRunPixelColorReader(Color.from_hex(args.dry_run_color))
            except ValueError as exc:
                print(f"script run configuration failed: {exc}", file=sys.stderr)
                return 2
        ScriptRunner(device=DryRunInputDevice(), color_reader=color_reader).run(script)
        return 0

    from game_automation.adapters.macos import MacOSPointerDevice

    color_reader = None
    if requirements.needs_color_reader:
        try:
            from game_automation.adapters.desktop import PyAutoGuiPixelColorReader

            color_reader = PyAutoGuiPixelColorReader()
        except RuntimeError as exc:
            print(f"script run setup failed: {exc}", file=sys.stderr)
            return 1

    ScriptRunner(device=MacOSPointerDevice(), color_reader=color_reader).run(script)
    return 0


def _run_recorder(args: argparse.Namespace) -> int:
    """启动坐标记录工具。"""
    from game_automation.adapters.desktop import (
        PyAutoGuiPixelColorReader,
        PyAutoGuiPointerPositionReader,
        TerminalKeyStateReader,
    )
    from game_automation.tools.coordinate_recorder import CoordinateRecorder

    key_reader = None
    try:
        key_reader = TerminalKeyStateReader()
        recorder = CoordinateRecorder(
            pointer_reader=PyAutoGuiPointerPositionReader(),
            key_reader=key_reader,
            color_reader=PyAutoGuiPixelColorReader(),
            display_interval_seconds=args.display_interval,
            poll_interval_seconds=args.poll_interval,
        )
        recorder.run()
    except RuntimeError as exc:
        print(f"coordinate recorder setup failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"coordinate recorder configuration failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if key_reader is not None:
            key_reader.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="star", description="Game automation toolkit.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List available scripts.")

    run_parser = subparsers.add_parser("run", help="Run a named script.")
    run_parser.add_argument("name", help="Script name to run.")
    mode = run_parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print planned operations without real mouse.")
    mode.add_argument("--macos", action="store_true", help="Run with macOS adapter (default).")
    run_parser.add_argument(
        "--dry-run-color",
        default="#000000",
        help="Fixed #RRGGBB screen color used when dry-running color conditions.",
    )

    recorder_parser = subparsers.add_parser("recorder", help="Record screen coordinates.")
    recorder_parser.add_argument("--display-interval", type=float, default=1.0, help="Seconds between coordinate prints.")
    recorder_parser.add_argument("--poll-interval", type=float, default=0.05, help="Seconds between keyboard polls.")

    args = parser.parse_args(argv)

    if args.command == "list":
        return _run_list()
    elif args.command == "run":
        return _run_script(args)
    elif args.command == "recorder":
        return _run_recorder(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
