"""实现脚本 runner，将领域动作转换为输入设备端口调用。"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from game_automation.core.ports import InputDevice
from game_automation.domain import Click, Drag, Script, Wait


Sleeper = Callable[[float], None]


@dataclass(frozen=True, slots=True)
class ScriptRunner:
    device: InputDevice
    sleeper: Sleeper = time.sleep

    def run(self, script: Script) -> None:
        """按脚本顺序执行所有动作。"""
        for action in script.actions:
            # 动作分派集中在 runner，避免 adapter 认识脚本领域对象。
            if isinstance(action, Click):
                self._run_click(script, action)
            elif isinstance(action, Drag):
                self._run_drag(script, action)
            elif isinstance(action, Wait):
                self._run_wait(action)
            else:  # pragma: no cover - 保护未来扩展时遗漏分派。
                raise TypeError(f"unsupported script action: {type(action).__name__}")

    def _run_click(self, script: Script, action: Click) -> None:
        """解析脚本级窗口中的点击点并执行点击。"""
        self.device.click(script.window.resolve(action.point))

    def _run_drag(self, script: Script, action: Drag) -> None:
        """解析脚本级窗口中的拖拽起止点并执行拖拽。"""
        start = script.window.resolve(action.start)
        end = script.window.resolve(action.end)
        self.device.drag_to(start, end, action.duration_seconds)

    def _run_wait(self, action: Wait) -> None:
        """执行等待动作，等待函数可在测试中注入。"""
        self.sleeper(action.duration_seconds)
