"""提供按脚本名称列出和运行脚本的通用命令行入口。"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from game_automation.cli import DryRunInputDevice, RecordedOperation
from game_automation.core import InputDevice, ScriptNotFoundError, ScriptRunner
from game_automation.scripts import DEFAULT_SCRIPT_CATALOG


def build_parser() -> argparse.ArgumentParser:
    """构建通用脚本命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="Manage and run named scripts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List available scripts.")

    run_parser = subparsers.add_parser("run", help="Run a named script.")
    run_parser.add_argument("name", help="Script name to run.")
    mode = run_parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print planned operations.")
    mode.add_argument(
        "--macos",
        action="store_true",
        help="Run with the macOS pointer adapter. This is the default mode.",
    )
    return parser


def _record_wait(device: DryRunInputDevice, duration_seconds: float) -> None:
    """dry-run 时记录等待动作但不真正休眠。"""
    device.operations.append(RecordedOperation("wait", duration_seconds=duration_seconds))


def _print_operations(operations: Sequence[RecordedOperation]) -> None:
    """逐行打印 dry-run 记录到的操作。"""
    for operation in operations:
        print(operation)


def main(argv: list[str] | None = None) -> int:
    """根据子命令列出脚本或按名称运行脚本。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        for name in DEFAULT_SCRIPT_CATALOG.list_names():
            print(name)
        return 0

    try:
        script = DEFAULT_SCRIPT_CATALOG.get(args.name)
    except ScriptNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not args.dry_run:
        # 真实执行时才导入 macOS adapter，保持列表和 dry-run 不依赖平台库。
        from game_automation.adapters.macos import MacOSPointerDevice

        ScriptRunner(device=MacOSPointerDevice()).run(script)
        return 0

    device: InputDevice = DryRunInputDevice()
    ScriptRunner(
        device=device,
        sleeper=lambda duration_seconds: _record_wait(device, duration_seconds),
    ).run(script)
    _print_operations(device.operations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
