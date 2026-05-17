"""实现脚本 runner，将领域动作转换为输入设备端口调用。"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.engine.ports import InputDevice
from game_automation.domain import Click, Drag, Script, Wait


@dataclass(frozen=True, slots=True)
class ScriptRunner:
    device: InputDevice

    def run(self, script: Script) -> None:
        """按脚本顺序执行所有动作。"""
        for action in script.actions:
            if isinstance(action, Click):
                self._run_click(script, action)
            elif isinstance(action, Drag):
                self._run_drag(script, action)
            elif isinstance(action, Wait):
                self._run_wait(action)
            else:  # pragma: no cover
                raise TypeError(f"unsupported script action: {type(action).__name__}")

    def _run_click(self, script: Script, action: Click) -> None:
        self.device.click(script.window.resolve(action.point))

    def _run_drag(self, script: Script, action: Drag) -> None:
        start = script.window.resolve(action.start)
        end = script.window.resolve(action.end)
        self.device.drag_to(start, end, action.duration_seconds)

    def _run_wait(self, action: Wait) -> None:
        self.device.wait(action.duration_seconds)
