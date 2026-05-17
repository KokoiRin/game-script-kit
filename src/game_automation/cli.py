"""提供 demo 命令行入口，负责选择 adapter 并启动 workflow。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field

from game_automation.core import InputDevice, run_demo_workflow
from game_automation.domain import Point


@dataclass(frozen=True, slots=True)
class RecordedOperation:
    name: str
    target: Point | None = None
    start: Point | None = None
    end: Point | None = None
    duration_seconds: float | None = None


@dataclass(slots=True)
class DryRunInputDevice:
    operations: list[RecordedOperation] = field(default_factory=list)

    def click(self, target: Point) -> None:
        """记录一次 dry-run 点击请求。"""
        self.operations.append(RecordedOperation("click", target=target))

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        """记录一次 dry-run 拖拽请求。"""
        self.operations.append(
            RecordedOperation(
                "drag_to",
                start=start,
                end=end,
                duration_seconds=duration_seconds,
            )
        )


def build_parser() -> argparse.ArgumentParser:
    """构建 demo 命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="Run the game automation demo workflow.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Run with a fake input device.")
    mode.add_argument("--macos", action="store_true", help="Run with the macOS pointer adapter.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """根据命令行参数选择真实 macOS adapter 或 dry-run 设备运行 demo。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.macos:
        # 只有真实 macOS 模式才导入 adapter，避免 dry-run 和核心逻辑依赖平台实现。
        from game_automation.adapters.macos import MacOSPointerDevice

        run_demo_workflow(MacOSPointerDevice())
        return 0

    device: InputDevice = DryRunInputDevice()
    run_demo_workflow(device)
    for operation in device.operations:
        print(operation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
