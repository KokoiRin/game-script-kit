"""验证 dry-run input adapter 的可观测输出。"""

from __future__ import annotations

from game_automation.adapters.dry_run import DryRunInputDevice
from game_automation.domain import Point


def test_dry_run_input_device_prints_click(capsys) -> None:
    """验证 dry-run 点击只打印目标坐标。"""
    DryRunInputDevice().click(Point(1, 2))

    assert capsys.readouterr().out == "click Point(x=1, y=2)\n"


def test_dry_run_input_device_prints_drag(capsys) -> None:
    """验证 dry-run 拖拽只打印起终点和持续时间。"""
    DryRunInputDevice().drag_to(Point(1, 2), Point(3, 4), duration_seconds=0.5)

    assert capsys.readouterr().out == "drag Point(x=1, y=2) -> Point(x=3, y=4) (duration=0.5s)\n"


def test_dry_run_input_device_prints_wait(capsys) -> None:
    """验证 dry-run 等待只打印持续时间。"""
    DryRunInputDevice().wait(0.25)

    assert capsys.readouterr().out == "wait 0.25s\n"
