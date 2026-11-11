"""解释脚本步骤树并调用已注入的运行端口。

本 module 只负责按领域步骤顺序驱动 InputDevice 和条件评估；它不创建 adapter、
不解析 CLI 参数，也不做脚本注册表查找。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Callable
from itertools import count
from time import monotonic

from game_automation.portable.domain import (
    Click,
    ClickTarget,
    Drag,
    Hotkey,
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
from game_automation.portable.engine.cancellation import ScriptCancelledError
from game_automation.portable.engine.condition_evaluator import evaluate_condition
from game_automation.portable.engine.image_query import locate_image, resolve_image_search
from game_automation.portable.engine.ports import (
    CancellationToken,
    InputDevice,
    PixelColorReader,
    RunLogger,
    ScreenImageLocator,
    ScreenStateReader,
    RuntimeControl,
)
from game_automation.portable.engine.run_events import ScriptRunEvent, emit_script_run_event


class ScriptStoppedNormally(RuntimeError):
    """表示脚本因前置条件未满足而正常停止。"""


class _RepeatInterrupted(Exception):
    """携带所属循环标识，防止内层循环误吞外层的中断。"""

    def __init__(self, owner: object, reason: str = "检测到中断图片，跳过本段剩余步骤") -> None:
        """记录本次中断对应的循环作用域和可展示原因。"""
        self.owner = owner
        self.reason = reason


@dataclass(frozen=True, slots=True)
class ScriptExecutionResult:
    """记录引擎是否完整执行脚本及正常停止原因。"""

    finish_reason: str = "completed"
    message: str | None = None


@dataclass(frozen=True, slots=True)
class ScriptRunner:
    device: InputDevice
    color_reader: PixelColorReader | None = None
    image_locator: ScreenImageLocator | None = None
    screen_state_reader: ScreenStateReader | None = None
    cancellation_token: CancellationToken | None = None
    logger: RunLogger | None = None
    emit_step_events: bool = False
    _step_guard: Callable[[], None] | None = None
    clock: Callable[[], float] = monotonic
    _deadline: float | None = None
    _deadline_owner: object | None = None
    runtime_control: RuntimeControl | None = None

    def run(self, script: Script) -> ScriptExecutionResult:
        """按脚本步骤树顺序执行所有步骤并返回可观察结束原因。"""
        try:
            self._run_steps(script, script.steps)
        except ScriptStoppedNormally as exc:
            return ScriptExecutionResult(
                finish_reason="stopped_unmet_condition",
                message=str(exc),
            )
        return ScriptExecutionResult()

    def _run_steps(self, script: Script, steps: tuple[Step, ...], *, path_prefix: str = "") -> None:
        """按顺序解释一组步骤。"""
        for index, step in enumerate(steps, start=1):
            step_path = f"{path_prefix}.{index}" if path_prefix else str(index)
            # 这些步骤在真正点击前或轮询内部检查，避免同一边界重复截图。
            self._raise_if_cancelled(check_guard=not isinstance(step, (Click, WaitUntil, Repeat)))
            self._run_step(script, step, step_path)
            self._raise_if_cancelled(check_guard=False)

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
            elif isinstance(step, Hotkey):
                self.device.hotkey(step.keys)
                self._emit_event(
                    "hotkey_performed",
                    step_path=step_path,
                    step_type="Hotkey",
                    details={"keys": "+".join(step.keys)},
                )
            elif isinstance(step, Repeat):
                self._run_repeat(script, step, step_path)
            elif isinstance(step, If):
                self._run_if(script, step, step_path)
            elif isinstance(step, WaitUntil):
                self._run_wait_until(script, step, step_path)
            else:  # pragma: no cover
                raise TypeError(f"unsupported script step: {type(step).__name__}")
        except _RepeatInterrupted:
            raise
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
        def prepare_and_click():
            """定位和守卫在同一未发送边界内，恢复后重新取证。"""
            target = self._resolve_click_target(script, action.point, step_path=step_path)
            self._raise_if_cancelled()
            self._emit_event(
                "click_resolved",
                step_path=step_path,
                step_type="Click",
                details={"point": str(target)},
            )
            self.device.click(target)
            return target

        target = (prepare_and_click() if self.runtime_control is None
                  else self.runtime_control.execute_input(prepare_and_click))
        self._emit_event(
            "click_performed",
            step_path=step_path,
            step_type="Click",
            details={"point": str(target)},
        )

        for hotkey in action.then_hotkeys:
            # 用户停止仍然立即生效；连续输入中不再截图，以免错过短暂在线窗口。
            self._raise_if_cancelled(check_guard=False)
            self.device.hotkey(hotkey.keys)
            self._emit_event("hotkey_performed", step_path=step_path, step_type="Hotkey",
                             details={"keys": "+".join(hotkey.keys)})

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
        self._wait(action.duration_seconds)
        self._emit_event(
            "wait_finished",
            step_path=step_path,
            step_type="Wait",
            details={"duration": str(action.duration_seconds)},
        )

    def _run_repeat(self, script: Script, step: Repeat, step_path: str) -> None:
        """按指定次数或无限执行循环，支持条件中断和用户取消。"""
        owner = object()

        def check_break() -> None:
            """先检查外层中断，再判断当前循环是否应提前结束。"""
            if self._step_guard is not None:
                self._step_guard()
            if evaluate_condition(step.break_if, window=script.window,
                                  color_reader=self.color_reader, image_locator=self.image_locator,
                                  screen_state_reader=self.screen_state_reader,
                                  resources=script.resources, logger=self.logger):
                raise _RepeatInterrupted(owner)

        deadline, deadline_owner = self._deadline, self._deadline_owner
        if step.max_seconds is not None:
            local_deadline = self.clock() + step.max_seconds
            if deadline is None or local_deadline < deadline:
                deadline, deadline_owner = local_deadline, owner
        runner = replace(self, _step_guard=self._step_guard if step.break_if is None else check_break,
                         _deadline=deadline, _deadline_owner=deadline_owner)
        try:
            for iteration in (count(1) if step.times is None else range(1, step.times + 1)):
                runner._raise_if_cancelled()
                self._emit_event(
                    "repeat_iteration_started", step_path=step_path, step_type="Repeat",
                    details={"iteration": str(iteration), "total": "无限" if step.times is None else str(step.times)},
                )
                runner._run_steps(script, step.steps, path_prefix=step_path)
        except _RepeatInterrupted as exc:
            if exc.owner is not owner:
                raise
            self._emit_event("repeat_interrupted", step_path=step_path, step_type="Repeat",
                             details={"reason": exc.reason})

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
            if step.timeout_seconds is not None and elapsed_seconds >= step.timeout_seconds:
                self._emit_event(
                    "wait_until_timed_out",
                    step_path=step_path,
                    step_type="WaitUntil",
                    details={"attempt": str(attempt), "elapsed_seconds": f"{elapsed_seconds:.3f}"},
                )
                raise ScriptStoppedNormally("等待条件未满足")

            wait_seconds = step.interval_seconds
            if step.timeout_seconds is not None:
                wait_seconds = min(wait_seconds, step.timeout_seconds - elapsed_seconds)
            self._wait(wait_seconds)
            self._raise_if_cancelled(check_guard=False)
            elapsed_seconds += wait_seconds
            attempt += 1

    def _wait(self, seconds: float) -> None:
        """等待不超过最早循环期限，平台调用的必要清理仍由adapter拥有。"""
        if self._deadline is not None:
            seconds = min(seconds, max(0.0, self._deadline - self.clock()))
        self.device.wait(seconds)

    def _check_deadline(self) -> None:
        """到期只中断拥有该期限的循环，不能被内层循环吞掉。"""
        if self._deadline is not None and self.clock() >= self._deadline:
            raise _RepeatInterrupted(self._deadline_owner, "已达到循环时间上限")

    def _raise_if_cancelled(self, *, check_guard: bool = True) -> None:
        """在脚本步骤边界发现取消信号时停止运行。"""
        if self.cancellation_token is not None and self.cancellation_token.is_cancelled():
            raise ScriptCancelledError("script run cancelled")
        self._check_deadline()
        if check_guard and self._step_guard is not None:
            self._step_guard()
            # 条件识别本身可能耗尽剩余时间，不能再发送当前动作。
            self._check_deadline()

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
            # 定位期间页面也可能变化；先让循环中断处理离开，再报告真正的缺图。
            self._raise_if_cancelled()
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
        """按脚本窗口解析图片目标的默认或显式搜索区域。"""
        return script.window.resolve_region(region)

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
