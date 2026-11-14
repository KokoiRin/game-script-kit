"""执行绑定窗口和资源的直接任务动作、观察及期限。

本模块拥有目标解析、输入准备、轮询、取消和操作事件。它只消费值对象与
已打开的运行端口，不解释任务文件、步骤树、条件语法或平台生命周期。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from functools import partial
from math import isfinite
from time import monotonic
from typing import TypeVar

from game_automation.portable.domain.color import Color
from game_automation.portable.domain.geometry import Point, Rect
from game_automation.portable.domain.image_matching import ImageMatch
from game_automation.portable.domain.input_keys import validate_hotkey_keys
from game_automation.portable.domain.point_aliases import (
    ImageRef,
    PointRef,
    SearchRef,
    TargetCatalog,
)
from game_automation.portable.domain.target_offsets import OffsetTarget
from game_automation.portable.domain.targets import ImageTarget
from game_automation.portable.domain.windows import Window
from game_automation.portable.engine.cancellation import (
    RunCancelled,
    ScriptCancelledError,
)
from game_automation.portable.engine.image_query import (
    ImageSearchSource,
    locate_image,
    resolve_image_search,
)
from game_automation.portable.engine.ports import (
    CancellationToken,
    InputDevice,
    PixelColorReader,
    RunLogger,
    RuntimeControl,
    ScreenImageLocator,
    ScreenStateReader,
)
from game_automation.portable.engine.run_events import (
    ScriptRunEvent,
    emit_script_run_event,
)

_Result = TypeVar("_Result")
Target = Point | PointRef | ImageTarget | OffsetTarget
_ZERO_OFFSET = Point(0, 0)


class TaskTimeout(TimeoutError):
    """表示一个具有独立身份的有效任务时间作用域已到期。"""

    def __init__(self, scope_id: str, message: str = "任务等待或限时段已到期") -> None:
        """保存到期作用域，让调用方只处理自己拥有的期限。"""
        super().__init__(message)
        self.scope_id = scope_id


class TargetNotFound(RuntimeError):
    """表示必需图片在真正准备输入时未找到。"""


@dataclass(slots=True)
class _Scope:
    """保存当前执行线程拥有的期限及调用检查点。"""

    identifier: str
    expires_at: float | None
    checkpoint: Callable[[], None] | None
    expired: bool = False


class TaskContext:
    """直接执行本次运行中的动作，统一维护输入和期限不变量。"""

    def __init__(
        self,
        window: Window,
        resources: TargetCatalog,
        *,
        device: InputDevice,
        clock: Callable[[], float] = monotonic,
        cancellation_token: CancellationToken | None = None,
        color_reader: PixelColorReader | None = None,
        image_locator: ScreenImageLocator | None = None,
        screen_state_reader: ScreenStateReader | None = None,
        runtime_control: RuntimeControl | None = None,
        logger: RunLogger | None = None,
        emit_step_events: bool = False,
    ) -> None:
        """接受已绑定窗口、资源及端口，初始化本线程的操作与作用域身份。"""
        self.window = window
        self.resources = resources
        self.device = device
        self.clock = clock
        self.cancellation_token = cancellation_token
        self.color_reader = color_reader
        self.image_locator = image_locator
        self.screen_state_reader = screen_state_reader
        self.runtime_control = runtime_control
        self.logger = logger
        self.emit_step_events = emit_step_events
        self._sequence = 0
        self._scope_sequence = 0
        self._scopes: list[_Scope] = []
        self._checking_checkpoints = False

    def find(
        self, image: str | ImageSearchSource, *, min_confidence: float | None = None
    ) -> ImageMatch | None:
        """解析命名或内联图片查询，未命中返回 None。"""
        source = self._image_source(image)
        _validate_confidence(min_confidence)
        with self.operation("Observe", summary=f"find {image}"):
            return self._locate(source, min_confidence=min_confidence)

    def click(
        self,
        target: str | Target,
        *,
        then_hotkeys: tuple[tuple[str, ...], ...] = (),
        path: str | None = None,
    ) -> None:
        """在同一准备边界定位并点击，连续按键之间仅检查取消和期限。"""
        for keys in then_hotkeys:
            validate_hotkey_keys(keys)
        target = PointRef(target) if isinstance(target, str) else target
        with self.operation(
            "Click", path=path, summary=f"click {target}", check_guard=False
        ) as action_path:

            def prepare_and_click() -> Point:
                """恢复后重新定位，在最终检查通过后才提交一次点击。"""
                resolved = self._resolve_target(target, action_path)
                self.check_cancelled()
                self.emit_event(
                    "click_resolved",
                    step_path=action_path,
                    step_type="Click",
                    details={"point": str(resolved)},
                )
                self.device.click(resolved)
                return resolved

            resolved = self._input(prepare_and_click)
            self.emit_event(
                "click_performed",
                step_path=action_path,
                step_type="Click",
                details={"point": str(resolved)},
            )
            for keys in then_hotkeys:
                # 连续输入不再截图，避免错过短暂有效的输入窗口。
                self.check_cancelled(check_guard=False)
                self._input(partial(self._send_hotkey, keys, action_path))

    def click_image(
        self,
        name: str | ImageSearchSource,
        *,
        timeout: float = 0,
        interval: float = 0.5,
        offset: Point = _ZERO_OFFSET,
        min_confidence: float | None = None,
        then_hotkeys: tuple[tuple[str, ...], ...] = (),
    ) -> None:
        """按需等待图片，在输入提交前重新定位，并保持连续按键边界。"""
        _validate_seconds(timeout, name="timeout", allow_zero=True)
        _validate_seconds(interval, name="interval")
        _validate_confidence(min_confidence)
        for keys in then_hotkeys:
            validate_hotkey_keys(keys)
        if timeout > 0:
            self.wait_image(
                name, timeout=timeout, interval=interval, min_confidence=min_confidence
            )
        self.click(
            ImageTarget(
                self._image_source(name), offset=offset, min_confidence=min_confidence
            ),
            then_hotkeys=then_hotkeys,
        )

    def wait_image(
        self,
        name: str | ImageSearchSource,
        *,
        timeout: float | None,
        interval: float = 0.5,
        min_confidence: float | None = None,
    ) -> ImageMatch:
        """等待图片出现并返回匹配，有限等待到期抛可恢复超时。"""
        source = self._image_source(name)
        _validate_confidence(min_confidence)
        return self.wait_for(
            lambda: self._locate(source, min_confidence=min_confidence),
            timeout=timeout,
            interval=interval,
            summary=f"wait_image {name}",
        )

    def state(self, *, min_confidence: float = 0.8) -> str:
        """从本次运行的状态端口读取当前画面。"""
        _validate_confidence(min_confidence)
        with self.operation("Observe", summary="state"):
            return self._read_state(min_confidence)

    def wait_state(
        self,
        name: str,
        *,
        timeout: float | None,
        interval: float = 0.5,
        min_confidence: float = 0.8,
    ) -> None:
        """等待指定画面状态，有限等待到期抛可恢复超时。"""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("screen state name must not be empty")
        _validate_confidence(min_confidence)
        self.wait_for(
            lambda: self._read_state(min_confidence) == name,
            timeout=timeout,
            interval=interval,
            summary=f"wait_state {name}",
        )

    def color(self, point: str | Point | PointRef) -> Color:
        """读取固定窗口内点位的当前颜色。"""
        target = PointRef(point) if isinstance(point, str) else point
        with self.operation("Observe", summary=f"color {point}"):
            resolved = self.window.resolve(self.resources.resolve_point(target))
            if self.color_reader is None:
                raise RuntimeError("color reader is required for color lookup")
            return self.color_reader.read_color(resolved)

    def drag(
        self, start: Point, end: Point, *, duration: float = 0, path: str | None = None
    ) -> None:
        """把窗口内起止点转换后，通过一次输入准备提交原子拖拽。"""
        _validate_seconds(duration, name="duration", allow_zero=True)
        with self.operation(
            "Drag", path=path, summary=f"drag {start} {end}"
        ) as action_path:

            def prepare_and_drag() -> None:
                """在最终检查后提交拖拽，平台拥有必要释放。"""
                resolved_start, resolved_end = (
                    self.window.resolve(start),
                    self.window.resolve(end),
                )
                self.check_cancelled(check_guard=False)
                self.emit_event(
                    "drag_resolved",
                    step_path=action_path,
                    step_type="Drag",
                    details={
                        "start": str(resolved_start),
                        "end": str(resolved_end),
                        "duration": str(duration),
                    },
                )
                self.device.drag_to(resolved_start, resolved_end, duration)

            self._input(prepare_and_drag)

    def wait(self, seconds: float, *, path: str | None = None) -> None:
        """执行可取消等待，并裁短到最早作用域的剩余预算。"""
        _validate_seconds(seconds, name="seconds", allow_zero=True)
        with self.operation(
            "Wait", path=path, summary=f"wait {seconds}"
        ) as action_path:
            self.emit_event(
                "wait_started",
                step_path=action_path,
                step_type="Wait",
                details={"duration": str(seconds)},
            )
            self.pause(seconds)
            self.emit_event(
                "wait_finished",
                step_path=action_path,
                step_type="Wait",
                details={"duration": str(seconds)},
            )

    def hotkey(self, *keys: str, path: str | None = None) -> None:
        """通过一次输入准备发送组合键，原子释放由设备负责。"""
        validate_hotkey_keys(keys)
        with self.operation(
            "Hotkey", path=path, summary=f"hotkey {keys}"
        ) as action_path:
            self._input(lambda: self._send_hotkey(keys, action_path))

    def check_cancelled(self, *, check_guard: bool = True) -> None:
        """先检查终止取消，再检查最早期限及当前所有作用域的检查点。"""
        self._check_cancellation()
        self._check_deadline()
        if check_guard and not self._checking_checkpoints:
            self._checking_checkpoints = True
            try:
                for scope in self._scopes:
                    if scope.checkpoint is not None:
                        try:
                            scope.checkpoint()
                        except BaseException:
                            self._check_cancellation()
                            raise
                        self.check_cancelled(check_guard=False)
            finally:
                self._checking_checkpoints = False

    @contextmanager
    def deadline(self, seconds: float) -> Iterator[str]:
        """为一段任务设置独立期限，嵌套时由最早期限拥有超时。"""
        with self.scope(seconds=seconds) as scope_id:
            yield scope_id

    @contextmanager
    def scope(
        self,
        *,
        seconds: float | None = None,
        checkpoint: Callable[[], None] | None = None,
    ) -> Iterator[str]:
        """组合通用期限和动作检查点，并保留各层独立身份。"""
        if seconds is not None:
            _validate_seconds(seconds, name="seconds")
        self.check_cancelled(check_guard=False)
        self._scope_sequence += 1
        scope = _Scope(
            f"scope.{self._scope_sequence}",
            None if seconds is None else self.clock() + seconds,
            checkpoint,
        )
        self._scopes.append(scope)
        if seconds is not None:
            self.emit_event(
                "scope_started", step_path=scope.identifier, step_type="Scope"
            )
        try:
            yield scope.identifier
            self.check_cancelled(check_guard=False)
        finally:
            self._scopes.pop()
            if seconds is not None:
                self.emit_event(
                    "scope_finished",
                    step_path=scope.identifier,
                    step_type="Scope",
                    status="timed_out" if scope.expired else "finished",
                )

    def pause(self, seconds: float) -> None:
        """为轮询和动作共用一次无嵌套事件的有界设备等待。"""
        self.check_cancelled(check_guard=False)
        expiry = self._earliest_deadline()
        if expiry is not None:
            seconds = min(seconds, max(0.0, expiry.expires_at - self.clock()))
        try:
            self.device.wait(seconds)
        except ScriptCancelledError as exc:
            raise RunCancelled(str(exc)) from exc
        self.check_cancelled(check_guard=False)

    def wait_for(
        self,
        query: Callable[[], _Result],
        *,
        timeout: float | None,
        interval: float,
        summary: str = "wait_for",
    ) -> _Result:
        """以有效任务时间轮询任意观察，定位成本和等待共用期限。"""
        _validate_seconds(interval, name="interval")
        if timeout is not None:
            _validate_seconds(timeout, name="timeout")
        with self.deadline(timeout) if timeout is not None else nullcontext():
            with self.operation(
                "Observe", summary=summary, check_guard=False
            ) as action_path:
                started_at = self.clock()
                attempt = 0
                while True:
                    self.check_cancelled()
                    value = query()
                    self.check_cancelled(check_guard=False)
                    attempt += 1
                    details = {
                        "attempt": str(attempt),
                        "result": str(bool(value)),
                        "elapsed_seconds": f"{self.clock() - started_at:.3f}",
                    }
                    self.emit_event(
                        "condition_evaluated",
                        step_path=action_path,
                        step_type="Observe",
                        details=details,
                    )
                    if value:
                        self.emit_event(
                            "wait_until_satisfied",
                            step_path=action_path,
                            step_type="Observe",
                            details=details,
                        )
                        return value
                    self.pause(interval)

    @contextmanager
    def operation(
        self,
        name: str,
        *,
        path: str | None = None,
        summary: str = "",
        check_guard: bool = True,
    ) -> Iterator[str]:
        """为当前动作分配独立身份并记录执行结果。"""
        self.check_cancelled(check_guard=check_guard)
        if path is None:
            self._sequence += 1
            path = str(self._sequence)
        self.emit_event(
            "step_started", step_path=path, step_type=name, details={"summary": summary}
        )
        try:
            yield path
            self.check_cancelled(check_guard=False)
        except ScriptCancelledError as exc:
            raise RunCancelled(str(exc)) from exc
        except TaskTimeout as exc:
            self._check_cancellation()
            self.emit_event(
                "step_stopped",
                step_path=path,
                step_type=name,
                status="timed_out",
                details={"reason": str(exc), "scope_id": exc.scope_id},
            )
            raise
        except TargetNotFound as exc:
            self._check_cancellation()
            self.emit_event(
                "step_stopped",
                step_path=path,
                step_type=name,
                status="stopped",
                details={"reason": str(exc)},
            )
            raise
        except Exception as exc:
            self._check_cancellation()
            self.emit_event(
                "step_failed",
                step_path=path,
                step_type=name,
                status="failed",
                details={"error": str(exc)},
            )
            raise
        else:
            self.emit_event(
                "step_succeeded", step_path=path, step_type=name, status="succeeded"
            )

    def emit_event(
        self,
        event_type: str,
        *,
        step_path: str = "",
        step_type: str = "",
        status: str = "",
        details: dict[str, str] | None = None,
    ) -> None:
        """按需输出已经发生的操作或作用域事件。"""
        if self.emit_step_events:
            emit_script_run_event(
                self.logger,
                ScriptRunEvent(
                    event_type,
                    step_path,
                    step_type,
                    status,
                    {} if details is None else details,
                ),
            )

    def _check_cancellation(self) -> None:
        """让用户终止优先于同一边界上的超时或普通平台故障。"""
        if (
            self.cancellation_token is not None
            and self.cancellation_token.is_cancelled()
        ):
            raise RunCancelled("script run cancelled")

    def _earliest_deadline(self) -> _Scope | None:
        """选取最早到期的作用域，等时刻时保留外层拥有者。"""
        return min(
            (scope for scope in self._scopes if scope.expires_at is not None),
            key=lambda scope: scope.expires_at,
            default=None,
        )

    def _check_deadline(self) -> None:
        """只给真正到期的作用域记录事件，异常携带其独立身份。"""
        scope = self._earliest_deadline()
        if scope is not None and self.clock() >= scope.expires_at:
            if not scope.expired:
                scope.expired = True
                self.emit_event(
                    "scope_expired",
                    step_path=scope.identifier,
                    step_type="Scope",
                    status="timed_out",
                )
            raise TaskTimeout(scope.identifier)

    def _input(self, operation: Callable[[], _Result]) -> _Result:
        """让平台只重做尚未提交的输入准备，并统一取消信号。"""
        try:
            return (
                operation()
                if self.runtime_control is None
                else self.runtime_control.execute_input(operation)
            )
        except ScriptCancelledError as exc:
            raise RunCancelled(str(exc)) from exc

    def _send_hotkey(self, keys: tuple[str, ...], path: str) -> None:
        """在组合键提交前检查取消与期限，并记录一次已发送输入。"""
        self.check_cancelled(check_guard=False)
        self.device.hotkey(keys)
        self.emit_event(
            "hotkey_performed",
            step_path=path,
            step_type="Hotkey",
            details={"keys": "+".join(keys)},
        )

    def _image_source(self, image: str | ImageSearchSource) -> ImageSearchSource:
        """优先把资源目录中的搜索名称解析为命名搜索。"""
        if isinstance(image, str):
            if any(search.name == image for search in self.resources.searches):
                return SearchRef(image)
            return ImageRef(image)
        return image

    def _locate(
        self,
        source: ImageSearchSource,
        *,
        region: Rect | None = None,
        min_confidence: float | None = None,
    ) -> ImageMatch | None:
        """集中解析命名资源、窗口搜索区域和置信度，再读取一次图像。"""
        return locate_image(
            source,
            image_locator=self.image_locator,
            resources=self.resources,
            region=region,
            region_resolver=self.window.resolve_region,
            min_confidence=min_confidence,
            logger=self.logger,
        ).match

    def _resolve_target(self, target: Target, path: str) -> Point:
        """把纯目标值解析为本次固定窗口中的最终屏幕坐标。"""
        if isinstance(target, (Point, PointRef)):
            return self.window.resolve(self.resources.resolve_point(target))
        if isinstance(target, OffsetTarget):
            base = self._resolve_target(target.base, path)
            return base.offset(x=target.offset.x, y=target.offset.y)
        if not isinstance(target, ImageTarget):
            raise TypeError(f"unsupported click target: {type(target).__name__}")
        search = resolve_image_search(
            target.template,
            resources=self.resources,
            region=target.region,
            min_confidence=target.min_confidence,
        )
        match = self._locate(
            target.template, region=target.region, min_confidence=target.min_confidence
        )
        if match is None:
            self.check_cancelled()
            self.emit_event(
                "image_target_missing",
                step_path=path,
                step_type="Click",
                details={"template": search.template.path},
            )
            raise TargetNotFound("图片目标未找到")
        resolved = match.point_at(target.anchor).offset(
            x=target.offset.x, y=target.offset.y
        )
        self.emit_event(
            "image_target_resolved",
            step_path=path,
            step_type="Click",
            details={"template": search.template.path, "point": str(resolved)},
        )
        return resolved

    def _read_state(self, min_confidence: float) -> str:
        """拒绝未装配的状态能力，并读取本次运行的状态端口。"""
        if self.screen_state_reader is None:
            raise RuntimeError("screen state reader is required for state lookup")
        return self.screen_state_reader.read_current_state(
            min_confidence=min_confidence, logger=self.logger
        )


def _validate_seconds(value: float, *, name: str, allow_zero: bool = False) -> None:
    """在作者接口边界拒绝非有限数值、布尔值及不合法时间。"""
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError(f"{name} must be finite seconds")
    if value < 0 or (value == 0 and not allow_zero):
        boundary = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be {boundary} finite seconds")


def _validate_confidence(value: float | None) -> None:
    """在观察入口校验可选置信度，保持资源默认阈值。"""
    if value is not None and (type(value) not in (int, float) or not 0 < value <= 1):
        raise ValueError("min_confidence must be greater than 0 and at most 1")
