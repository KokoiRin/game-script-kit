"""提供独立坐标记录工具命令行入口。"""

from __future__ import annotations

import argparse
import sys

from game_automation.adapters.desktop import (
    PyAutoGuiPointerPositionReader,
    TerminalKeyStateReader,
)
from game_automation.core import AdapterSetupError
from game_automation.tools.coordinate_recorder import CoordinateRecorder


def build_parser() -> argparse.ArgumentParser:
    """构建坐标记录工具的命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="Record screen coordinates for game scripts.")
    parser.add_argument(
        "--display-interval",
        type=float,
        default=1.0,
        help="Seconds between coordinate prints.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.05,
        help="Seconds between keyboard polls.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """组装真实 adapter 并启动坐标记录工具。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    key_reader: TerminalKeyStateReader | None = None

    try:
        key_reader = TerminalKeyStateReader()
        recorder = CoordinateRecorder(
            pointer_reader=PyAutoGuiPointerPositionReader(),
            key_reader=key_reader,
            display_interval_seconds=args.display_interval,
            poll_interval_seconds=args.poll_interval,
        )
        recorder.run()
    except AdapterSetupError as exc:
        print(f"coordinate recorder setup failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"coordinate recorder configuration failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if key_reader is not None:
            key_reader.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
