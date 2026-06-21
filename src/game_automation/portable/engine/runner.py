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
from game_automation.portable.engine.image_query import locate_image, resolve_image_search
from game_automation.portable.engine.ports import (
    CancellationToken,
    InputDevice,
    PixelColorReader,
    RunLogger,
    ScreenImageLocator,
    ScreenStateReader,
)
from game_automation.portable.engine.run_events import ScriptRunEvent, emit_script_run_event


class ScriptCancelledError(RuntimeError):
    """表示脚本运行被外部取消信号停止。"""


class ScriptStoppedNormally(RuntimeError):
    """表示脚本因前置条件未满足而正常停止。"""


@dataclass(frozen=True, slots=True)
class ScriptRunner:
    device: InputDevice
    color_reader: PixelColorReader | None = None
    image_locator: ScreenImageLocator | None = None
    screen_state_reader: ScreenStateReader | None = None
    cancellation_token: CancellationToken | None = None
    logger: RunLogger | None = None
    emit_step_events: bool = False

    def run(self, script: Script) -> None:
        """按脚本步骤树顺序执行所有步骤。"""
        try:
            self._run_steps(script, script.steps)
        except ScriptStoppedNormally:
            return

    def _run_steps(self, script: Script, steps: tuple[Step, ...], *, path_prefix: str = "") -> None:
        """按顺序解释一组步骤。"""
        for index, step in enumerate(steps, start=1):
            step_path = f"{path_prefix}.{index}" if path_prefix else str(index)
            self._raise_if_cancelled()
            self._run_step(script, step, step_path)
            self._raise_if_cancelled()

    def _run_step(self, script: Script, step: Step, step_path: str) -> None:
        """解释单个步骤并触发对应运行时行为。"""
        step_type = type(step).__name__
        self._emit_event(
            "step_started",
            step_path=step_path,
            step_type=step_type,
            details={"summary": repr(step)},
        )
        try:
            if isinstance(step, Click):
                self._run_click(script, step, step_path)
            elif isinstance(step, Drag):
                self._run_drag(script, step, step_path)
            elif isinstance(step, Wait):
                self._run_wait(step, step_path)
            elif isinstance(step, Repeat):
                self._run_repeat(script, step, step_path)
            elif isinstance(step, If):
                self._run_if(script, step, step_path)
            elif isinstance(step, WaitUntil):
                self._run_wait_until(script, step, step_path)
            else:  # pragma: no cover
                raise TypeError(f"unsupported script step: {type(step).__name__}")
        except ScriptStoppedNormally as exc:
            self._emit_event(
                "step_stopped",
                step_path=step_path,
                step_type=step_type,
                status="stopped",
                details={"reason": str(exc)},
            )
            raise
        except Exception as exc:
            self._emit_event(
                "step_failed",
                step_path=step_path,
                step_type=step_type,
                status="failed",
                details={"error": str(exc)},
            )
            raise
        self._emit_event(
            "step_succeeded",
            step_path=step_path,
            step_type=step_type,
            status="succeeded",
        )

    def _run_click(self, script: Script, action: Click, step_path: str) -> None:
        """解析脚本窗口内点击点并调用输入设备。"""
        target = self._resolve_click_target(script, action.point, step_path=step_path)
        self._emit_event(
            "click_resolved",
            step_path=step_path,
            step_type="Click",
            details={"point": str(target)},
        )
        self.device.click(target)
        self._emit_event(
            "click_performed",
            step_path=step_path,
            step_type="Click",
            details={"point": str(target)},
        )

    def _run_drag(self, script: Script, action: Drag, step_path: str) -> None:
        """解析脚本窗口内拖拽起止点并调用输入设备。"""
        start = script.window.resolve(action.start)
        end = script.window.resolve(action.end)
        self._emit_event(
            "drag_resolved",
            step_path=step_path,
            step_type="Drag",
            details={"start": str(start), "end": str(end), "duration": str(action.duration_seconds)},
        )
        self.device.drag_to(start, end, action.duration_seconds)

    def _run_wait(self, action: Wait, step_path: str) -> None:
        """调用输入设备等待指定时长。"""
        self._emit_event(
            "wait_started",
            step_path=step_path,
            step_type="Wait",
            details={"duration": str(action.duration_seconds)},
        )
        self.device.wait(action.duration_seconds)
        self._emit_event(
            "wait_finished",
            step_path=step_path,
            step_type="Wait",
            details={"duration": str(action.duration_seconds)},
        )

    def _run_repeat(self, script: Script, step: Repeat, step_path: str) -> None:
        """按固定次数递归执行 Repeat 内部步骤。"""
        for iteration in range(1, step.times + 1):
            self._emit_event(
                "repeat_iteration_started",
                step_path=step_path,
                step_type="Repeat",
                details={"iteration": str(iteration), "total": str(step.times)},
            )
            self._run_steps(script, step.steps, path_prefix=step_path)

    def _run_if(self, script: Script, step: If, step_path: str) -> None:
        """按条件结果递归执行 then 或 else 分支。"""
        matched = evaluate_condition(
            step.condition,
            window=script.window,
            color_reader=self.color_reader,
            image_locator=self.image_locator,
            screen_state_reader=self.screen_state_reader,
            resources=script.resources,
            logger=self.logger,
        )
        branch = "then" if matched else "else"
        self._emit_event(
            "condition_evaluated",
            step_path=step_path,
            step_type="If",
            details={"result": str(matched), "branch": branch},
        )
        if matched:
            self._run_steps(script, step.then_steps, path_prefix=f"{step_path}.then")
        else:
            self._run_steps(script, step.else_steps, path_prefix=f"{step_path}.else")

    def _run_wait_until(self, script: Script, step: WaitUntil, step_path: str) -> None:
        """轮询条件直到满足或超时。"""
        elapsed_seconds = 0.0
        attempt = 1
        while True:
            self._raise_if_cancelled()
            matched = evaluate_condition(
                step.condition,
                window=script.window,
                color_reader=self.color_reader,
                image_locator=self.image_locator,
                screen_state_reader=self.screen_state_reader,
                resources=script.resources,
                logger=self.logger,
            )
            self._emit_event(
                "condition_evaluated",
                step_path=step_path,
                step_type="WaitUntil",
                details={
                    "attempt": str(attempt),
                    "result": str(matched),
                    "elapsed_seconds": f"{elapsed_seconds:.3f}",
                },
            )
            if matched:
                self._emit_event(
                    "wait_until_satisfied",
                    step_path=step_path,
                    step_type="WaitUntil",
                    details={"attempt": str(attempt), "elapsed_seconds": f"{elapsed_seconds:.3f}"},
                )
                return
            if elapsed_seconds >= step.timeout_seconds:
                self._emit_event(
                    "wait_until_timed_out",
                    step_path=step_path,
                    step_type="WaitUntil",
                    details={"attempt": str(attempt), "elapsed_seconds": f"{elapsed_seconds:.3f}"},
                )
                raise ScriptStoppedNormally("等待条件未满足")

            remaining_seconds = step.timeout_seconds - elapsed_seconds
            wait_seconds = min(step.interval_seconds, remaining_seconds)
            self.device.wait(wait_seconds)
            self._raise_if_cancelled()
            elapsed_seconds += wait_seconds
            attempt += 1

    def _raise_if_cancelled(self) -> None:
        """在脚本步骤边界发现取消信号时停止运行。"""
        if self.cancellation_token is not None and self.cancellation_token.is_cancelled():
            raise ScriptCancelledError("script run cancelled")

    def _resolve_click_target(self, script: Script, target: ClickTarget, *, step_path: str) -> Point:
        """把静态或图片点击目标解析成最终屏幕坐标。"""
        if isinstance(target, Point):
            return script.window.resolve(target)
        if isinstance(target, PointRef):
            return script.window.resolve(script.resources.resolve_point(target))
        if isinstance(target, OffsetTarget):
            base = self._resolve_click_target(script, target.base, step_path=step_path)
            return base.offset(x=target.offset.x, y=target.offset.y)
        if isinstance(target, ImageTarget):
            return self._resolve_image_target(script, target, step_path=step_path)
        raise TypeError(f"unsupported click target: {type(target).__name__}")

    def _resolve_image_target(self, script: Script, target: ImageTarget, *, step_path: str) -> Point:
        """通过图像定位端口把图片目标解析成屏幕坐标。"""
        if self.image_locator is None:
            raise RuntimeError("image locator is required for image targets")
        search = resolve_image_search(
            target.template,
            resources=script.resources,
            region=target.region,
            min_confidence=target.min_confidence,
        )
        result = locate_image(
            target.template,
            image_locator=self.image_locator,
            resources=script.resources,
            region=target.region,
            region_resolver=lambda region: self._resolve_image_target_region(script, region),
            min_confidence=target.min_confidence,
            logger=self.logger,
        )
        match = result.match
        if match is None:
            self._emit_event(
                "image_target_missing",
                step_path=step_path,
                step_type="Click",
                details={"template": search.template.path},
            )
            raise ScriptStoppedNormally("图片目标未找到")
        anchor_point = match.point_at(target.anchor)
        resolved = Point(
            anchor_point.x + target.offset.x,
            anchor_point.y + target.offset.y,
        )
        self._emit_event(
            "image_target_resolved",
            step_path=step_path,
            step_type="Click",
            details={"template": search.template.path, "point": str(resolved)},
        )
        return resolved

    def _resolve_image_target_region(self, script: Script, region: Rect | None) -> Rect | None:
        """按脚本窗口解析图片目标搜索区域左上角。"""
        if region is None:
            return None
        top_left = script.window.resolve(Point(region.left, region.top))
        return Rect(top_left.x, top_left.y, region.width, region.height)

    def _emit_event(
        self,
        event_type: str,
        *,
        step_path: str = "",
        step_type: str = "",
        status: str = "",
        details: dict[str, str] | None = None,
    ) -> None:
        """按需输出结构化步骤事件。"""
        if not self.emit_step_events:
            return
        emit_script_run_event(
            self.logger,
            ScriptRunEvent(
                event_type=event_type,
                step_path=step_path,
                step_type=step_type,
                status=status,
                details={} if details is None else details,
            ),
        )
