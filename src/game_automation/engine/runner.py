"""实现脚本 runner，将领域步骤转换为输入设备端口调用。"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.domain import Click, Drag, If, Repeat, Script, Step, Wait
from game_automation.engine.condition_evaluator import evaluate_condition
from game_automation.engine.ports import InputDevice, PixelColorReader


@dataclass(frozen=True, slots=True)
class ScriptRunner:
    device: InputDevice
    color_reader: PixelColorReader | None = None

    def run(self, script: Script) -> None:
        """按脚本步骤树顺序执行所有步骤。"""
        self._run_steps(script, script.steps)

    def _run_steps(self, script: Script, steps: tuple[Step, ...]) -> None:
        """按顺序解释一组步骤。"""
        for step in steps:
            self._run_step(script, step)

    def _run_step(self, script: Script, step: Step) -> None:
        """解释单个步骤并触发对应运行时行为。"""
        if isinstance(step, Click):
            self._run_click(script, step)
        elif isinstance(step, Drag):
            self._run_drag(script, step)
        elif isinstance(step, Wait):
            self._run_wait(step)
        elif isinstance(step, Repeat):
            self._run_repeat(script, step)
        elif isinstance(step, If):
            self._run_if(script, step)
        else:  # pragma: no cover
            raise TypeError(f"unsupported script step: {type(step).__name__}")

    def _run_click(self, script: Script, action: Click) -> None:
        """解析脚本窗口内点击点并调用输入设备。"""
        self.device.click(script.window.resolve(action.point))

    def _run_drag(self, script: Script, action: Drag) -> None:
        """解析脚本窗口内拖拽起止点并调用输入设备。"""
        start = script.window.resolve(action.start)
        end = script.window.resolve(action.end)
        self.device.drag_to(start, end, action.duration_seconds)

    def _run_wait(self, action: Wait) -> None:
        """调用输入设备等待指定时长。"""
        self.device.wait(action.duration_seconds)

    def _run_repeat(self, script: Script, step: Repeat) -> None:
        """按固定次数递归执行 Repeat 内部步骤。"""
        for _ in range(step.times):
            self._run_steps(script, step.steps)

    def _run_if(self, script: Script, step: If) -> None:
        """按条件结果递归执行 then 或 else 分支。"""
        if evaluate_condition(
            step.condition,
            window=script.window,
            color_reader=self.color_reader,
        ):
            self._run_steps(script, step.then_steps)
        else:
            self._run_steps(script, step.else_steps)
