"""提供已记录坐标点击脚本的命令行入口。"""

from __future__ import annotations

import argparse

from game_automation.cli import DryRunInputDevice, RecordedOperation
from game_automation.core import InputDevice, run_recorded_click_script


def build_parser() -> argparse.ArgumentParser:
    """构建已记录坐标点击脚本的命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="Run the recorded click script.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print planned clicks only.")
    mode.add_argument("--macos", action="store_true", help="Run with the macOS pointer adapter.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """根据命令行参数选择 dry-run 或真实 macOS adapter 运行脚本。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.macos:
        # 真实执行时才导入 macOS adapter，保持脚本核心不依赖平台库。
        from game_automation.adapters.macos import MacOSPointerDevice

        run_recorded_click_script(MacOSPointerDevice())
        return 0

    device: InputDevice = DryRunInputDevice()
    def record_wait(duration_seconds: float) -> None:
        """dry-run 时记录等待动作但不真正休眠。"""
        device.operations.append(
            RecordedOperation("wait", duration_seconds=duration_seconds)
        )

    run_recorded_click_script(device, sleeper=record_wait)
    for operation in device.operations:
        print(operation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
