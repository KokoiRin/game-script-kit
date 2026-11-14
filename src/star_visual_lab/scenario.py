"""定义视觉靶场任务处理台的确定状态机。

本 module 负责状态转换、加载时间、故障模式和真值事件；它不处理 HTTP、
不渲染页面，也不导入 Star 的脚本或平台实现。
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

SUPPORTED_MODES = ("normal", "slow", "missing_target")
DEFAULT_LOADING_DELAYS = {
    "normal": 0.6,
    "slow": 3.0,
    "missing_target": 0.6,
}


class ScenarioActionError(ValueError):
    """表示动作不允许在当前靶场状态执行。"""


@dataclass(frozen=True, slots=True)
class ScenarioSnapshot:
    """保存测试程序和页面可读取的当前场景真值。"""

    scenario: str
    state: str
    mode: str
    sequence: int
    available_actions: tuple[str, ...]
    loading_delay_seconds: float


@dataclass(frozen=True, slots=True)
class ScenarioEvent:
    """记录一次重置、用户动作或自动状态转换。"""

    sequence: int
    kind: str
    action: str | None
    from_state: str | None
    to_state: str


class TaskFlowScenario:
    """驱动任务处理台从主页到完成页的状态转换。"""

    def __init__(
        self,
        *,
        mode: str = "normal",
        loading_delay_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """初始化场景并记录第一条重置事件。"""
        self._clock = clock
        self._lock = threading.RLock()
        self._state = "home"
        self._mode = "normal"
        self._loading_delay_seconds = 0.0
        self._loading_until: float | None = None
        self._events: list[ScenarioEvent] = []
        self.reset(mode=mode, loading_delay_seconds=loading_delay_seconds)

    def snapshot(self) -> ScenarioSnapshot:
        """刷新到期转换并返回当前场景快照。"""
        with self._lock:
            self._refresh_loading()
            return self._snapshot()

    def events(self) -> tuple[ScenarioEvent, ...]:
        """刷新到期转换并按顺序返回事件快照。"""
        with self._lock:
            self._refresh_loading()
            return tuple(self._events)

    def perform(self, action: str) -> ScenarioSnapshot:
        """执行当前状态允许的页面动作并返回动作后的快照。"""
        with self._lock:
            self._refresh_loading()
            if action not in self._available_actions():
                raise ScenarioActionError(
                    f"action {action} is not allowed in state {self._state}"
                )
            from_state = self._state
            if action == "open_tasks":
                self._state = "task_list"
            elif action == "select_target":
                self._state = "loading"
                self._loading_until = self._clock() + self._loading_delay_seconds
            elif action == "confirm_task":
                self._state = "completed"
            else:  # pragma: no cover - allowed actions are closed above.
                raise ScenarioActionError(f"unsupported scenario action: {action}")
            self._append_event(
                kind="action",
                action=action,
                from_state=from_state,
                to_state=self._state,
            )
            return self._snapshot()

    def reset(
        self,
        *,
        mode: str = "normal",
        loading_delay_seconds: float | None = None,
    ) -> ScenarioSnapshot:
        """使用指定模式和延迟把场景恢复到主页。"""
        _validate_mode(mode)
        resolved_delay = (
            DEFAULT_LOADING_DELAYS[mode]
            if loading_delay_seconds is None
            else float(loading_delay_seconds)
        )
        _validate_loading_delay(resolved_delay)
        with self._lock:
            self._state = "home"
            self._mode = mode
            self._loading_delay_seconds = resolved_delay
            self._loading_until = None
            self._events = []
            self._append_event(
                kind="reset",
                action=None,
                from_state=None,
                to_state="home",
            )
            return self._snapshot()

    def _refresh_loading(self) -> None:
        """在加载期限到达后记录自动进入确认页的转换。"""
        if self._state != "loading" or self._loading_until is None:
            return
        if self._clock() < self._loading_until:
            return
        self._state = "confirm"
        self._loading_until = None
        self._append_event(
            kind="transition",
            action=None,
            from_state="loading",
            to_state="confirm",
        )

    def _snapshot(self) -> ScenarioSnapshot:
        """在持锁状态下构造无需再次刷新的快照。"""
        return ScenarioSnapshot(
            scenario="task-flow",
            state=self._state,
            mode=self._mode,
            sequence=self._events[-1].sequence,
            available_actions=self._available_actions(),
            loading_delay_seconds=self._loading_delay_seconds,
        )

    def _available_actions(self) -> tuple[str, ...]:
        """返回当前状态和故障模式允许的动作。"""
        if self._state == "home":
            return ("open_tasks",)
        if self._state == "task_list" and self._mode != "missing_target":
            return ("select_target",)
        if self._state == "confirm":
            return ("confirm_task",)
        return ()

    def _append_event(
        self,
        *,
        kind: str,
        action: str | None,
        from_state: str | None,
        to_state: str,
    ) -> None:
        """向当前事件序列追加一条带稳定序号的记录。"""
        self._events.append(
            ScenarioEvent(
                sequence=len(self._events) + 1,
                kind=kind,
                action=action,
                from_state=from_state,
                to_state=to_state,
            )
        )


def _validate_mode(mode: str) -> None:
    """拒绝未声明的靶场故障模式。"""
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported visual lab mode: {mode}")


def _validate_loading_delay(delay: float) -> None:
    """拒绝负数加载延迟。"""
    if delay < 0:
        raise ValueError("visual lab loading delay must be greater than or equal to 0")
