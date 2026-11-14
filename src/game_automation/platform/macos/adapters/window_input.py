"""为固定窗口进程投递 macOS 原生输入事件。

固定使用前台会话原生投递；发送前核对绑定进程与遮挡，不重试其他 transport。
不依赖 PyAutoGUI；坐标、新帧门槛及资源所有权仍由窗口会话管理。
"""

import math
import time

# ANSI 虚拟键码；修饰键与普通键统一由一份表解释。
KEY_CODES = dict(
    zip(
        (
            "a",
            "s",
            "d",
            "f",
            "h",
            "g",
            "z",
            "x",
            "c",
            "v",
            "b",
            "q",
            "w",
            "e",
            "r",
            "y",
            "t",
            "1",
            "2",
            "3",
            "4",
            "6",
            "5",
            "=",
            "9",
            "7",
            "-",
            "8",
            "0",
            "]",
            "o",
            "u",
            "[",
            "i",
            "p",
            "l",
            "j",
            "'",
            "k",
            ";",
            "\\",
            ",",
            "/",
            "n",
            "m",
            ".",
        ),
        (
            0,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            29,
            30,
            31,
            32,
            33,
            34,
            35,
            37,
            38,
            39,
            40,
            41,
            42,
            43,
            44,
            45,
            46,
            47,
        ),
        strict=True,
    )
)
KEY_CODES.update(
    {
        "enter": 36,
        "return": 36,
        "tab": 48,
        "space": 49,
        "`": 50,
        "backspace": 51,
        "escape": 53,
        "esc": 53,
        "command": 55,
        "cmd": 55,
        "win": 55,
        "shift": 56,
        "option": 58,
        "alt": 58,
        "control": 59,
        "ctrl": 59,
        "delete": 117,
        "home": 115,
        "end": 119,
        "pageup": 116,
        "pagedown": 121,
        "left": 123,
        "right": 124,
        "down": 125,
        "up": 126,
        "f1": 122,
        "f2": 120,
        "f3": 99,
        "f4": 118,
        "f5": 96,
        "f6": 97,
        "f7": 98,
        "f8": 100,
        "f9": 101,
        "f10": 109,
        "f11": 103,
        "f12": 111,
    }
)
MODIFIER_FLAGS = {
    55: "kCGEventFlagMaskCommand",
    56: "kCGEventFlagMaskShift",
    58: "kCGEventFlagMaskAlternate",
    59: "kCGEventFlagMaskControl",
}


class MacOSWindowInputDevice:
    def __init__(
        self,
        session,
        *,
        quartz=None,
        clock=time.monotonic,
        sleep=time.sleep,
        activation=None,
        appkit=None,
        frontmost_pid=None,
        keyboard_focus=None,
    ):
        """借用会话绑定的 Quartz 和进程，不查找新的目标。"""
        self.session = session
        self.q = session.binding.quartz if quartz is None else quartz
        self.pid = int(session.window.id.split(":", 1)[0])
        self._clock, self._sleep = clock, sleep
        self._activation = (
            _activate_bound_application if activation is None else activation
        )
        self._appkit = appkit
        self._event_number = 0
        self._frontmost_pid = (
            _read_frontmost_pid if frontmost_pid is None else frontmost_pid
        )
        self._mouse_held = False
        self._keyboard_focus = (
            _read_keyboard_focus if keyboard_focus is None else keyboard_focus
        )

    def _prepare_input(self):
        """仅激活已绑定 PID，确认成为前台应用后才允许投递。"""
        self.session.check_window()
        frontmost = self._activation(
            self.pid, self.session.check_window, self._clock, self._sleep
        )
        if frontmost != self.pid:
            raise RuntimeError(
                f"原生输入目标未成为前台应用：expected_pid={self.pid} frontmost_pid={frontmost}"
            )
        self.session.check_window()
        logger = getattr(self.session, "logger", None)
        if logger is not None:
            logger.log(
                f"input transport=foreground-session backend=macos-window pid={self.pid} frontmost_pid={frontmost} window_id={self.session.binding.number}"
            )

    def _check_foreground(self):
        """每次实际发送前重新确认绑定进程仍是前台应用。"""
        self.session.check_window()
        frontmost = self._frontmost_pid()
        if frontmost != self.pid:
            raise RuntimeError(
                f"原生前台输入已失焦：expected_pid={self.pid} frontmost_pid={frontmost}"
            )

    def _check_unobscured(self, point):
        """按系统前后顺序命中点位，首个可见窗口必须是固定 CG ID。"""
        from game_automation.platform.macos.adapters.window_identity import (
            logical_bounds,
        )

        q = self.q
        rows = (
            q.CGWindowListCopyWindowInfo(
                q.kCGWindowListOptionOnScreenOnly
                | q.kCGWindowListExcludeDesktopElements,
                q.kCGNullWindowID,
            )
            or ()
        )
        cursor_level = (
            q.CGWindowLevelForKey(q.kCGCursorWindowLevelKey)
            if hasattr(q, "CGWindowLevelForKey")
            and hasattr(q, "kCGCursorWindowLevelKey")
            else None
        )
        for row in rows:
            # 系统光标也是一个可见窗口；仅精确排除公开光标层，不忽略其他高层浮窗。
            if cursor_level is not None and row.get(q.kCGWindowLayer) == cursor_level:
                continue
            try:
                alpha = float(row.get(q.kCGWindowAlpha, 1.0))
            except TypeError, ValueError:
                continue
            if not math.isfinite(alpha) or alpha <= 0:
                continue
            bounds = logical_bounds(row.get(q.kCGWindowBounds, {}))
            if bounds is None:
                continue
            left, top, width, height = bounds
            if (
                width <= 0
                or height <= 0
                or not (
                    left <= point.x < left + width and top <= point.y < top + height
                )
            ):
                continue
            if row.get(q.kCGWindowNumber) != self.session.binding.number:
                raise RuntimeError(
                    f"原生输入点位被其他窗口遮挡：target_window_id={self.session.binding.number} covering_window_id={row.get(q.kCGWindowNumber)}"
                )
            return
        raise RuntimeError("原生输入点位没有命中固定目标窗口，已停止点击")

    def _release_mouse(self, point):
        """只释放已经尝试发送的按下事件，必要释放不被失焦拦截。"""
        if self._mouse_held:
            try:
                self._mouse(self.q.kCGEventLeftMouseUp, point)
            finally:
                self._mouse_held = False

    def _mouse(self, kind, point):
        """构造窗口关联事件，并经唯一的前台会话 transport 投递。"""
        q = self.q
        appkit = _load_appkit() if self._appkit is None else self._appkit
        event_types = {
            q.kCGEventMouseMoved: appkit.NSEventTypeMouseMoved,
            q.kCGEventLeftMouseDown: appkit.NSEventTypeLeftMouseDown,
            q.kCGEventLeftMouseUp: appkit.NSEventTypeLeftMouseUp,
            q.kCGEventLeftMouseDragged: appkit.NSEventTypeLeftMouseDragged,
        }
        r = self.session.window.rect
        # NSEvent 使用窗口基坐标，原点在左下；port 输入仍是屏幕左上逻辑坐标。
        local = (point.x - r.left, r.height - (point.y - r.top))
        self._event_number += 1
        native_event = appkit.NSEvent.mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(
            event_types[kind],
            local,
            0,
            self._clock(),
            self.session.binding.number,
            None,
            self._event_number,
            1,
            0.0 if kind in (q.kCGEventMouseMoved, q.kCGEventLeftMouseUp) else 1.0,
        )
        event = None if native_event is None else native_event.CGEvent()
        if event is None:
            raise RuntimeError("无法创建与固定窗口关联的原生鼠标事件")
        # 当前进程不拥有目标 NSWindow，NSEvent 无法推算外部窗口的屏幕原点。
        q.CGEventSetLocation(event, (point.x, point.y))
        logger = getattr(self.session, "logger", None)
        if logger is not None:
            cg_point = (
                q.CGEventGetLocation(event)
                if hasattr(q, "CGEventGetLocation")
                else None
            )
            logger.log(
                f"input mouse transport=foreground-session constructor=NSEvent kind={kind} global_point={point} window_point={local} cg_point={cg_point}"
            )
        q.CGEventSetIntegerValueField(event, q.kCGMouseEventClickState, 1)
        for name in (
            "kCGMouseEventWindowUnderMousePointer",
            "kCGMouseEventWindowUnderMousePointerThatCanHandleThisEvent",
        ):
            if hasattr(q, name):
                q.CGEventSetIntegerValueField(
                    event, getattr(q, name), self.session.binding.number
                )
        if kind != q.kCGEventLeftMouseUp:
            self._check_foreground()
            if kind == q.kCGEventLeftMouseDown:
                self._check_unobscured(point)
                self._mouse_held = True
        q.CGEventPost(q.kCGSessionEventTap, event)

    def click(self, target):
        """投递移动、按下与配对释放，并要求后续读取新的源事件。"""
        self.session.validate_point(target)
        self._prepare_input()
        q = self.q
        try:
            self._mouse(q.kCGEventMouseMoved, target)
            try:
                self._mouse(q.kCGEventLeftMouseDown, target)
                # 游戏可能按帧轮询按下状态，零间隔释放会被整个采样周期跳过。
                self.wait(0.05)
            finally:
                self._release_mouse(target)
        finally:
            self.session.input_finished()
        self.session.check_window()

    def hotkey(self, keys):
        """按序发送按键并在失败或取消后逆序释放已尝试按下的键。"""
        self.session.check_window()
        codes = []
        for key in keys:
            try:
                codes.append(KEY_CODES[key.lower()])
            except KeyError as exc:
                raise ValueError(f"原生输入不支持按键 {key!r}") from exc
        self._prepare_input()
        held, flags = [], 0
        try:
            for code in codes:
                self.session.check_cancelled()
                next_flags = (
                    flags | getattr(self.q, MODIFIER_FLAGS[code])
                    if code in MODIFIER_FLAGS
                    else flags
                )

                def register_attempt(code=code, next_flags=next_flags):
                    """校验成功且即将投递时才登记，投递后异常仍需要释放。"""
                    nonlocal flags
                    held.append(code)
                    flags = next_flags

                self._key(code, True, next_flags, on_attempt=register_attempt)
        finally:
            release_error = None
            for code in reversed(held):
                if code in MODIFIER_FLAGS:
                    flags &= ~getattr(self.q, MODIFIER_FLAGS[code])
                try:
                    self._key(code, False, flags)
                except Exception as exc:
                    release_error = exc
            self.session.input_finished()
            if release_error is not None:
                raise release_error
        self.session.check_window()

    def _key(self, code, down, flags, *, on_attempt=None):
        """核对前台后发送键盘事件，释放事件始终保留。"""
        event = self.q.CGEventCreateKeyboardEvent(None, code, down)
        if event is None:
            raise RuntimeError("无法创建原生键盘事件")
        self.q.CGEventSetFlags(event, flags)
        if down:
            self._check_foreground()
            focused = self._keyboard_focus(self.pid)
            if (
                focused.title != self.session.window.title
                or focused.rect != self.session.window.rect
            ):
                raise RuntimeError("原生键盘焦点窗口与固定目标不符，已停止按键")
            if on_attempt is not None:
                on_attempt()
        self.q.CGEventPost(self.q.kCGSessionEventTap, event)

    def drag_to(self, start, end, duration_seconds=0.0):
        """窗口内有界插值拖动，异常时仍配对释放鼠标。"""
        if not math.isfinite(duration_seconds) or duration_seconds < 0:
            raise ValueError("drag duration must be finite and nonnegative")
        self.session.validate_point(start)
        self.session.validate_point(end)
        self._prepare_input()
        q, last = self.q, start
        try:
            self._mouse(q.kCGEventMouseMoved, start)
            try:
                self._mouse(q.kCGEventLeftMouseDown, start)
                count = max(1, math.ceil(duration_seconds / 0.02))
                for index in range(1, count + 1):
                    self.session.check_window()
                    if duration_seconds:
                        self.wait(duration_seconds / count)
                    last = type(start)(
                        round(start.x + (end.x - start.x) * index / count),
                        round(start.y + (end.y - start.y) * index / count),
                    )
                    self._mouse(q.kCGEventLeftMouseDragged, last)
            finally:
                self._release_mouse(last)
        finally:
            self.session.input_finished()
        self.session.check_window()

    def wait(self, duration_seconds):
        """小片等待并检查取消与窗口身份，不阻塞整段脚本。"""
        if not math.isfinite(duration_seconds) or duration_seconds < 0:
            raise ValueError("wait duration must be finite and nonnegative")
        deadline = self._clock() + duration_seconds
        while True:
            self.session.check_window()
            remaining = deadline - self._clock()
            if remaining <= 0:
                return
            self._sleep(min(0.05, remaining))


def _activate_bound_application(pid, check_window, clock, sleep):
    """用公开 AX 应用级前台请求绑定进程，并有界核对真实前台 PID。"""
    import AppKit

    application = AppKit.NSRunningApplication.runningApplicationWithProcessIdentifier_(
        pid
    )
    if application is None or application.isTerminated():
        raise RuntimeError("原生输入目标进程已经退出")
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    check_window()
    frontmost = workspace.frontmostApplication()
    frontmost_pid = None if frontmost is None else int(frontmost.processIdentifier())
    if frontmost_pid == pid:
        return frontmost_pid
    import ApplicationServices as accessibility

    ax_application = accessibility.AXUIElementCreateApplication(pid)
    ax_error = accessibility.AXUIElementSetAttributeValue(
        ax_application, accessibility.kAXFrontmostAttribute, True
    )
    if ax_error != accessibility.kAXErrorSuccess:
        raise RuntimeError(f"原生输入前台请求被系统拒绝：pid={pid} ax_error={ax_error}")
    deadline = clock() + 1.0
    while True:
        check_window()
        frontmost = workspace.frontmostApplication()
        frontmost_pid = (
            None if frontmost is None else int(frontmost.processIdentifier())
        )
        if frontmost_pid == pid:
            return frontmost_pid
        if clock() >= deadline:
            raise RuntimeError(
                f"原生输入目标激活超时：expected_pid={pid} frontmost_pid={frontmost_pid} ax_error={ax_error}"
            )
        sleep(0.02)


def _load_appkit():
    """仅在原生鼠标事件构造时加载系统 AppKit。"""
    import AppKit

    return AppKit


def _read_frontmost_pid():
    """只读获取系统当前前台 PID，不能用先前激活结果替代。"""
    appkit = _load_appkit()
    application = appkit.NSWorkspace.sharedWorkspace().frontmostApplication()
    return None if application is None else int(application.processIdentifier())


def _read_keyboard_focus(pid):
    """只读取绑定 PID 的 AXFocusedWindow，不重新搜索或 Raise 窗口。"""
    from game_automation.platform.macos.adapters.accessibility_window_backend import (
        MacOSAccessibilityWindowBackend,
    )

    return MacOSAccessibilityWindowBackend().read_focused_window(pid)
