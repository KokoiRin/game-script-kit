"""提供显式后台点击试验，不激活应用、不移动真实指针。

复用运行会话的窗口身份、取消与输入后新帧契约；仅通过PID投递一套事件，
私有CGEventSetWindowLocation缺失即失败，不回退前台输入或其他transport。
"""
from itertools import count
import math
import time

BACKGROUND_DISPATCH_FLAG = 0x00100000  # Command位，按外部实测recipe用于后台投递；不是NonCoalesced。
_EVENT_NUMBERS = count(1)


def load_window_location_setter():
    """只绑定私有事件字段setter；绑定本身不创建或投递事件。"""
    try:
        import objc
        import Quartz  # 确保CGEventRef的CF桥接类型已登记。
        from Foundation import NSBundle
        bundle = NSBundle.bundleWithPath_('/System/Library/Frameworks/CoreGraphics.framework')
        functions = {}
        objc.loadBundleFunctions(bundle, functions,
            [('CGEventSetWindowLocation', b'v^{__CGEvent=}{CGPoint=dd}', 'private window-local event setter')],
            skip_undefined=False)
        setter = functions.get('CGEventSetWindowLocation')
        if not callable(setter):
            raise RuntimeError('private symbol was not resolved')
        return setter
    except Exception as exc:
        raise RuntimeError('后台点击试验依赖私有CGEventSetWindowLocation，当前系统无法绑定；不会改用其他输入方式') from exc


class MacOSBackgroundWindowInputDevice:
    def __init__(self, session, *, appkit=None, window_location_setter=None,
                 frontmost_pid=None, clock=time.monotonic, sleep=time.sleep):
        """借用固定会话并显式解析试验依赖，不请求前台或捕获UI缓存。"""
        self.session = session
        self.q = session.binding.quartz
        self.pid = int(session.window.id.split(':', 1)[0])
        self._appkit = appkit
        self._set_window_location = load_window_location_setter() if window_location_setter is None else window_location_setter
        self._frontmost_pid = self._read_frontmost_pid if frontmost_pid is None else frontmost_pid
        self._clock, self._sleep = clock, sleep
        self._held = False
        self._last_frontmost_pid = None

    def _framework(self):
        """仅在后台点击真正需要时加载AppKit。"""
        if self._appkit is None:
            import AppKit
            return AppKit
        return self._appkit

    def _read_frontmost_pid(self):
        """只读系统前台进程，不激活或按名称重新查找应用。"""
        frontmost = self._framework().NSWorkspace.sharedWorkspace().frontmostApplication()
        return None if frontmost is None else int(frontmost.processIdentifier())

    def _require_background(self):
        """确保本轮确实测试后台，已前台或无法核实前台均不发送。"""
        self.session.check_window()
        frontmost = self._frontmost_pid()
        if frontmost is None:
            raise RuntimeError('后台点击试验无法确认当前前台进程，已停止')
        if frontmost == self.pid:
            raise RuntimeError('后台点击试验要求目标保持后台；当前游戏已是前台，已停止')
        self._last_frontmost_pid = frontmost
        return frontmost

    def _mouse(self, kind, point, *, release=False):
        """构造完整单一路径事件，保留NSEvent自动填充的窗口字段。"""
        q, appkit = self.q, self._framework()
        frontmost = self._last_frontmost_pid if release else self._require_background()
        types = {q.kCGEventMouseMoved:appkit.NSEventTypeMouseMoved,
                 q.kCGEventLeftMouseDown:appkit.NSEventTypeLeftMouseDown,
                 q.kCGEventLeftMouseUp:appkit.NSEventTypeLeftMouseUp}
        rect = self.session.window.rect
        base = (point.x - rect.left, rect.height - (point.y - rect.top))
        native = appkit.NSEvent.mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(
            types[kind], base, 0, self._clock(), self.session.binding.number, None, next(_EVENT_NUMBERS), 1,
            1.0 if kind == q.kCGEventLeftMouseDown else 0.0)
        event = None if native is None else native.CGEvent()
        if event is None:
            raise RuntimeError('后台点击试验无法构造NSEvent关联事件')
        q.CGEventSetLocation(event, (point.x, point.y))
        screen = q.CGEventGetLocation(event)
        sx, sy = (screen.x, screen.y) if hasattr(screen, 'x') else screen
        local = (sx - rect.left, sy - rect.top)
        self._set_window_location(event, local)
        for field, value in ((q.kCGMouseEventButtonNumber, 0), (q.kCGMouseEventSubtype, 3),
                             (q.kCGMouseEventClickState, 1),
                             (q.kCGMouseEventWindowUnderMousePointer, self.session.binding.number),
                             (q.kCGMouseEventWindowUnderMousePointerThatCanHandleThisEvent, self.session.binding.number)):
            q.CGEventSetIntegerValueField(event, field, value)
        q.CGEventSetFlags(event, BACKGROUND_DISPATCH_FLAG)
        logger = self.session.logger
        if logger is not None:
            logger.log(f'input transport=background-pid-experiment backend=macos-window-background pid={self.pid} '
                       f'frontmost_pid={frontmost} frontmost_evidence={"cached-release" if release else "checked"} window_id={self.session.binding.number} kind={kind} '
                       f'global_point={point} window_local={local} subtype=3 flags=0x100000 private_window_location=True')
        if not release:
            self._require_background()
        if kind == q.kCGEventLeftMouseDown:
            self._held = True
        q.CGEventPostToPid(self.pid, event)

    def click(self, target):
        """后台投递primer、按下和50ms后配对释放，并撤销旧视觉证明。"""
        self.session.validate_point(target)
        self._require_background()
        try:
            self._mouse(self.q.kCGEventMouseMoved, target)
            try:
                self._mouse(self.q.kCGEventLeftMouseDown, target)
                self.wait(0.05)
            finally:
                if self._held:
                    try:
                        self._mouse(self.q.kCGEventLeftMouseUp, target, release=True)
                    finally:
                        self._held = False
        finally:
            self.session.input_finished()
        self._require_background()

    def wait(self, duration_seconds):
        """等待时只检查窗口与取消，不请求前台。"""
        if not math.isfinite(duration_seconds) or duration_seconds < 0:
            raise ValueError('wait duration must be finite and nonnegative')
        deadline = self._clock() + duration_seconds
        while True:
            self.session.check_window()
            remaining = deadline - self._clock()
            if remaining <= 0:
                return
            self._sleep(min(0.02, remaining))

    def hotkey(self, keys):
        """明确拒绝尚未验证的后台键盘能力。"""
        raise NotImplementedError('后台点击试验尚不支持hotkey')

    def drag_to(self, start, end, duration_seconds=0.0):
        """明确拒绝尚未验证的后台拖拽能力。"""
        raise NotImplementedError('后台点击试验尚不支持drag')
