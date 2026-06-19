"""解释脚本步骤树并调用已注入的运行端口。

本 module 只负责按领域步骤顺序驱动 InputDevice 和条件评估；它不创建 adapter、
不解析 CLI 参数，也不做脚本注册表查找。
"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.portable.domain import (
    Click,
    ClickTarget,
    Drag,
    If,
    ImageTarget,
    OffsetTarget,
    Point,
    PointRef,
    Rect,
    Repeat,
    Script,
    Step,
    Wait,
    WaitUntil,
)
from game_automation.portable.engine.condition_evaluator import evaluate_condition
from game_automation.portable.engine.image_query import locate_image
from game_automation.portable.engine.ports import InputDevice, PixelColorReader, ScreenImageLocator


@dataclass(frozen=True, slots=True)
class ScriptRunner:
    device: InputDevice
    color_reader: PixelColorReader | None = None
    image_locator: ScreenImageLocator | None = None

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
        elif isinstance(step, WaitUntil):
            self._run_wait_until(script, step)
        else:  # pragma: no cover
            raise TypeError(f"unsupported script step: {type(step).__name__}")

    def _run_click(self, script: Script, action: Click) -> None:
        """解析脚本窗口内点击点并调用输入设备。"""
        self.device.click(self._resolve_click_target(script, action.point))

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
            image_locator=self.image_locator,
            resources=script.resources,
        ):
            self._run_steps(script, step.then_steps)
        else:
            self._run_steps(script, step.else_steps)

    def _run_wait_until(self, script: Script, step: WaitUntil) -> None:
        """轮询条件直到满足或超时。"""
        elapsed_seconds = 0.0
        while True:
            if evaluate_condition(
                step.condition,
                window=script.window,
                color_reader=self.color_reader,
                image_locator=self.image_locator,
                resources=script.resources,
            ):
                return
            if elapsed_seconds >= step.timeout_seconds:
                raise TimeoutError("wait until condition timed out")

            remaining_seconds = step.timeout_seconds - elapsed_seconds
            wait_seconds = min(step.interval_seconds, remaining_seconds)
            self.device.wait(wait_seconds)
            elapsed_seconds += wait_seconds

    def _resolve_click_target(self, script: Script, target: ClickTarget) -> Point:
        """把静态或图片点击目标解析成最终屏幕坐标。"""
        if isinstance(target, Point):
            return script.window.resolve(target)
        if isinstance(target, PointRef):
            return script.window.resolve(script.resources.resolve_point(target))
        if isinstance(target, OffsetTarget):
            base = self._resolve_click_target(script, target.base)
            return base.offset(x=target.offset.x, y=target.offset.y)
        if isinstance(target, ImageTarget):
            return self._resolve_image_target(script, target)
        raise TypeError(f"unsupported click target: {type(target).__name__}")

    def _resolve_image_target(self, script: Script, target: ImageTarget) -> Point:
        """通过图像定位端口把图片目标解析成屏幕坐标。"""
        if self.image_locator is None:
            raise RuntimeError("image locator is required for image targets")
        template = script.resources.resolve_image(target.template)
        result = locate_image(
            target.template,
            image_locator=self.image_locator,
            resources=script.resources,
            region=self._resolve_image_target_region(script, target.region),
            min_confidence=target.min_confidence,
        )
        match = result.match
        if match is None:
            raise RuntimeError(f"image target not found: {template.path}")
        anchor_point = match.point_at(target.anchor)
        return Point(
            anchor_point.x + target.offset.x,
            anchor_point.y + target.offset.y,
        )

    def _resolve_image_target_region(self, script: Script, region: Rect | None) -> Rect | None:
        """按脚本窗口解析图片目标搜索区域左上角。"""
        if region is None:
            return None
        top_left = script.window.resolve(Point(region.left, region.top))
        return Rect(top_left.x, top_left.y, region.width, region.height)
