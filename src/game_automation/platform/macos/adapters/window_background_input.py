"""提供显式后台点击试验，不激活应用、不移动真实指针。

复用运行会话的窗口身份、取消与输入后新帧契约；仅通过PID投递一套事件，
私有CGEventSetWindowLocation缺失即失败，不回退前台输入或其他transport。
"""

import math
import time
from contextlib import contextmanager
from importlib import import_module
from itertools import count

from game_automation.portable.domain import Point

BACKGROUND_DISPATCH_FLAG = (
    0x00100000  # Command位，按外部实测recipe用于后台投递；不是NonCoalesced。
)
_EVENT_NUMBERS = count(1)


def load_window_location_setter():
    """只绑定私有事件字段setter；绑定本身不创建或投递事件。"""
    try:
        import objc
        from Foundation import NSBundle

        import_module("Quartz")
        bundle = NSBundle.bundleWithPath_(
            "/System/Library/Frameworks/CoreGraphics.framework"
        )
        functions = {}
        objc.loadBundleFunctions(
            bundle,
            functions,
            [
                (
                    "CGEventSetWindowLocation",
                    b"v^{__CGEvent=}{CGPoint=dd}",
                    "private window-local event setter",
                )
            ],
            skip_undefined=False,
        )
        setter = functions.get("CGEventSetWindowLocation")
        if not callable(setter):
            raise RuntimeError("private symbol was not resolved")
        return setter
    except Exception as exc:
        raise RuntimeError(
            "后台点击试验依赖私有CGEventSetWindowLocation，当前系统无法绑定；不会改用其他输入方式"
        ) from exc


class MacOSBackgroundWindowInputDevice:
    def __init__(
        self,
        session,
        *,
        appkit=None,
        window_location_setter=None,
        frontmost_pid=None,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        """借用固定会话并显式解析试验依赖，不请求前台或捕获UI缓存。"""
        self.session = session
        self.q = session.binding.quartz
        self.pid = int(session.window.id.split(":", 1)[0])
        self._appkit = appkit
        self._set_window_location = (
            load_window_location_setter()
            if window_location_setter is None
            else window_location_setter
        )
        self._frontmost_pid = (
            self._read_frontmost_pid if frontmost_pid is None else frontmost_pid
        )
        self._clock, self._sleep = clock, sleep
        self._held = False
        self._held_local = None
        self._last_frontmost_pid = None

    def _framework(self):
        """仅在后台点击真正需要时加载AppKit。"""
        if self._appkit is None:
            import AppKit

            return AppKit
        return self._appkit

    def _read_frontmost_pid(self):
        """只读系统前台进程，不激活或按名称重新查找应用。"""
        frontmost = (
            self._framework().NSWorkspace.sharedWorkspace().frontmostApplication()
        )
        return None if frontmost is None else int(frontmost.processIdentifier())

    def _require_ready(self):
        """核对窗口可用性，前台PID只作为投递诊断。"""
        self.session.check_window()
        frontmost = self._frontmost_pid()
        self._last_frontmost_pid = frontmost
        return frontmost

    def _mouse(self, kind, point, *, release=False):
        """构造完整单一路径事件，保留NSEvent自动填充的窗口字段。"""
        q, appkit = self.q, self._framework()
        dragging = kind == q.kCGEventLeftMouseDragged
        frontmost = (
            self._last_frontmost_pid if release or dragging else self._require_ready()
        )
        types = {
            q.kCGEventMouseMoved: appkit.NSEventTypeMouseMoved,
            q.kCGEventLeftMouseDown: appkit.NSEventTypeLeftMouseDown,
            q.kCGEventLeftMouseUp: appkit.NSEventTypeLeftMouseUp,
            q.kCGEventLeftMouseDragged: appkit.NSEventTypeLeftMouseDragged,
        }
        rect = getattr(self.session, "rect", self.session.window.rect)
        if release and self._held_local is not None:
            if hasattr(self.session, "release_point"):
                point, rect = self.session.release_point(self._held_local)
            else:
                point = Point(
                    rect.left + self._held_local.x, rect.top + self._held_local.y
                )
        base = (point.x - rect.left, rect.height - (point.y - rect.top))
        native = appkit.NSEvent.mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(
            types[kind],
            base,
            0,
            self._clock(),
            self.session.binding.number,
            None,
            next(_EVENT_NUMBERS),
            1,
            1.0 if kind == q.kCGEventLeftMouseDown or dragging else 0.0,
        )
        event = None if native is None else native.CGEvent()
        if event is None:
            raise RuntimeError("后台点击试验无法构造NSEvent关联事件")
        q.CGEventSetLocation(event, (point.x, point.y))
        screen = q.CGEventGetLocation(event)
        sx, sy = (screen.x, screen.y) if hasattr(screen, "x") else screen
        local = (sx - rect.left, sy - rect.top)
        self._set_window_location(event, local)
        for field, value in (
            (q.kCGMouseEventButtonNumber, 0),
            (q.kCGMouseEventSubtype, 3),
            (q.kCGMouseEventClickState, 1),
            (q.kCGMouseEventWindowUnderMousePointer, self.session.binding.number),
            (
                q.kCGMouseEventWindowUnderMousePointerThatCanHandleThisEvent,
                self.session.binding.number,
            ),
        ):
            q.CGEventSetIntegerValueField(event, field, value)
        q.CGEventSetFlags(event, BACKGROUND_DISPATCH_FLAG)
        logger = self.session.logger
        if logger is not None:
            logger.log(
                f"input transport=background-pid-experiment backend=macos-window-background pid={self.pid} "
                f"frontmost_pid={frontmost} frontmost_evidence={'cached-release' if release else 'cached-drag' if dragging else 'checked'} window_id={self.session.binding.number} kind={kind} "
                f"global_point={point} window_local={local} subtype=3 flags=0x100000 private_window_location=True"
            )
        if dragging:
            # 已提交手势遇到展示中断，停止移动并立即释放，交回会话等待恢复。
            if self.session.check_window() == {}:
                return False
            self._held_local = Point(point.x - rect.left, point.y - rect.top)
        elif not release:
            self._require_ready()
        if kind == q.kCGEventLeftMouseDown:
            self.session.commit_input()
            self._held_local = Point(point.x - rect.left, point.y - rect.top)
            self._held = True
        q.CGEventPostToPid(self.pid, event)
        return True

    @contextmanager
    def _pressed(self, target):
        """投递按下，在退出或失败时释放最后的局部点并撤销旧帧。"""
        self.session.validate_point(target)
        self._require_ready()
        try:
            self._mouse(self.q.kCGEventMouseMoved, target)
            try:
                self._mouse(self.q.kCGEventLeftMouseDown, target)
                yield
            finally:
                if self._held:
                    try:
                        self._mouse(self.q.kCGEventLeftMouseUp, target, release=True)
                    finally:
                        self._held = False
        finally:
            self.session.input_finished()

    def click(self, target):
        """后台投递一次点击，按住五十毫秒后释放。"""
        with self._pressed(target):
            self._hold_mouse(0.05)

    def _hold_mouse(self, duration_seconds):
        """按住使用系统时间，只检查取消，保证及时进入释放路径。"""
        deadline = self._clock() + duration_seconds
        while True:
            self.session.check_cancelled()
            remaining = deadline - self._clock()
            if remaining <= 0:
                return
            self._sleep(min(0.02, remaining))

    def wait(self, duration_seconds):
        """以有效任务时间等待，展示暂停和取消由会话管理。"""
        if not math.isfinite(duration_seconds) or duration_seconds < 0:
            raise ValueError("wait duration must be finite and nonnegative")
        deadline = self.session.task_time() + duration_seconds
        while True:
            self.session.check_window()
            remaining = deadline - self.session.task_time()
            if remaining <= 0:
                return
            self._sleep(min(0.02, remaining))

    def hotkey(self, keys):
        """明确拒绝尚未验证的后台键盘能力。"""
        raise NotImplementedError("后台点击试验尚不支持hotkey")

    def drag_to(self, start, end, duration_seconds=0.0):
        """按住后沿窗口内线段投递移动，并在最后到达的位置释放。"""
        if not math.isfinite(duration_seconds) or duration_seconds < 0:
            raise ValueError("drag duration must be finite and nonnegative")
        self.session.validate_point(end)
        steps = max(1, math.ceil(duration_seconds / 0.02))
        with self._pressed(start):
            for index in range(1, steps + 1):
                self._hold_mouse(duration_seconds / steps)
                point = Point(
                    round(start.x + (end.x - start.x) * index / steps),
                    round(start.y + (end.y - start.y) * index / steps),
                )
                if not self._mouse(self.q.kCGEventLeftMouseDragged, point):
                    break
