"""验证原生前台输入的遮挡、焦点、事件字段与配对释放。"""

from types import SimpleNamespace

import pytest

from game_automation.platform.macos.adapters.window_input import MacOSWindowInputDevice
from game_automation.platform.macos.adapters.window_input import (
    _activate_bound_application as activate_bound_application,
)
from game_automation.portable.domain import Point, Rect
from game_automation.portable.engine.cancellation import TaskCancelledError


@pytest.fixture(autouse=True)
def fake_activation(monkeypatch):
    """默认只模拟前台确认，测试不得操作真实应用。"""
    from game_automation.platform.macos.adapters import window_input

    monkeypatch.setattr(
        window_input,
        "_activate_bound_application",
        lambda pid, check, clock, sleep: pid,
    )
    monkeypatch.setattr(window_input, "_load_appkit", lambda: AppKit)
    monkeypatch.setattr(window_input, "_read_frontmost_pid", lambda: 42)
    monkeypatch.setattr(
        window_input,
        "_read_keyboard_focus",
        lambda pid: SimpleNamespace(title="Game", rect=Rect(100, 200, 80, 60)),
    )


class AppKit:
    NSEventTypeMouseMoved = "move"
    NSEventTypeLeftMouseDown = "down"
    NSEventTypeLeftMouseUp = "up"
    NSEventTypeLeftMouseDragged = "drag"

    class NSEvent:
        @staticmethod
        def mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(
            kind, point, flags, stamp, number, context, event_number, count, pressure
        ):
            """模拟携带窗口基坐标与窗口编号的公开事件构造。"""
            return SimpleNamespace(
                CGEvent=lambda: {
                    "kind": kind,
                    "point": point,
                    "window-point": point,
                    "window-number": number,
                    "event-number": event_number,
                }
            )


class Quartz:
    kCGSessionEventTap = "foreground-session"
    kCGWindowListOptionOnScreenOnly = 1
    kCGWindowListExcludeDesktopElements = 2
    kCGNullWindowID = 0
    kCGWindowAlpha = "alpha"
    kCGWindowBounds = "bounds"
    kCGWindowNumber = "number"
    kCGWindowLayer = "layer"
    kCGCursorWindowLevelKey = "cursor-level-key"
    kCGMouseButtonLeft = 0
    kCGMouseEventClickState = "clicks"
    kCGMouseEventWindowUnderMousePointer = "window"
    kCGMouseEventWindowUnderMousePointerThatCanHandleThisEvent = "handling-window"
    kCGEventMouseMoved = "move"
    kCGEventLeftMouseDown = "down"
    kCGEventLeftMouseUp = "up"
    kCGEventLeftMouseDragged = "drag"
    kCGEventFlagMaskCommand = 1
    kCGEventFlagMaskShift = 2
    kCGEventFlagMaskAlternate = 4
    kCGEventFlagMaskControl = 8

    def __init__(self, fail=None):
        """保存目标事件并允许指定事件在投递后失败。"""
        self.events = []
        self.fail = fail
        self.rows = [
            {
                "number": 7,
                "alpha": 1,
                "bounds": {"X": 100, "Y": 200, "Width": 80, "Height": 60},
            }
        ]

    def CGEventCreateMouseEvent(self, source, kind, point, button):
        """建立模拟鼠标事件。"""
        return {"kind": kind, "point": point}

    def CGEventSetIntegerValueField(self, event, field, value):
        """登记公开的目标字段。"""
        event[field] = value

    def CGWindowLevelForKey(self, key):
        """提供系统公开的精确光标层级。"""
        assert key == self.kCGCursorWindowLevelKey
        return 2147483630

    def CGWindowListCopyWindowInfo(self, options, null_id):
        """按窗口服务器的前后顺序返回点位遮挡信息。"""
        return self.rows

    def CGEventPost(self, pid, event):
        """记录唯一允许的投递 API。"""
        self.events.append((pid, event))
        if self.fail == event["kind"]:
            raise RuntimeError("post failed")

    def CGEventCreateKeyboardEvent(self, source, code, down):
        """建立模拟键盘事件。"""
        return {"kind": (code, down)}

    def CGEventSetLocation(self, event, point):
        """明确设置最终 CGEvent 的全局逻辑点。"""
        event["point"] = point

    def CGEventSetFlags(self, event, flags):
        """登记修饰键状态。"""
        event["flags"] = flags


class Session:
    def __init__(self, quartz):
        """建立固定进程和窗口。"""
        self.binding = SimpleNamespace(quartz=quartz, number=7)
        self.window = SimpleNamespace(
            id="42:1", title="Game", rect=Rect(100, 200, 80, 60)
        )
        self.finished = 0
        self.cancelled = False

    def validate_point(self, point):
        """只允许测试窗口范围内输入。"""
        if not (100 <= point.x < 180 and 200 <= point.y < 260):
            raise ValueError("outside window")
        self.check_window()

    def check_window(self):
        """边界检查中保留取消。"""
        self.check_cancelled()

    def check_cancelled(self):
        """模拟协作式取消。"""
        if self.cancelled:
            raise TaskCancelledError("cancelled")

    def input_finished(self):
        """记录后续视觉读取门槛。"""
        self.finished += 1


def test_click_uses_foreground_session_and_bound_cg_window():
    """移动、按下、释放都使用唯一前台会话 transport 和固定窗口字段。"""
    q = Quartz()
    session = Session(q)
    MacOSWindowInputDevice(session).click(Point(105, 206))
    assert [e["kind"] for _, e in q.events] == ["move", "down", "up"]
    assert all(
        pid == q.kCGSessionEventTap
        and e["window"] == 7
        and e["handling-window"] == 7
        and e["clicks"] == 1
        for pid, e in q.events
    )
    assert session.finished == 1


def test_mouse_down_failure_still_posts_matching_up():
    """底层可能先发出按下再抛异常，仍必须释放。"""
    q = Quartz(fail="down")
    session = Session(q)
    with pytest.raises(RuntimeError, match="post failed"):
        MacOSWindowInputDevice(session).click(Point(105, 206))
    assert [e["kind"] for _, e in q.events] == ["move", "down", "up"]
    assert session.finished == 1


def test_invalid_point_never_posts_event():
    """全局坐标越界直接拒绝。"""
    q = Quartz()
    with pytest.raises(ValueError, match="outside"):
        MacOSWindowInputDevice(Session(q)).click(Point(5, 6))
    assert q.events == []


def test_hotkey_failure_releases_reverse_order_with_flags():
    """普通键失败后仍先释放普通键再释放修饰键。"""
    q = Quartz(fail=(0, True))
    session = Session(q)
    with pytest.raises(RuntimeError, match="post failed"):
        MacOSWindowInputDevice(session).hotkey(("command", "a"))
    assert [e["kind"] for _, e in q.events] == [
        (55, True),
        (0, True),
        (0, False),
        (55, False),
    ]
    assert [e["flags"] for _, e in q.events] == [1, 1, 1, 0]
    assert session.finished == 1


def test_hotkey_cancellation_releases_held_modifier():
    """取消不阻止必要的按键释放。"""
    q = Quartz()
    session = Session(q)
    original = q.CGEventPost

    def post(pid, event):
        """首键发出后触发取消。"""
        original(pid, event)
        session.cancelled = True

    q.CGEventPost = post
    with pytest.raises(TaskCancelledError):
        MacOSWindowInputDevice(session).hotkey(("ctrl", "a"))
    assert [e["kind"] for _, e in q.events] == [(59, True), (59, False)]


def test_drag_exception_releases_mouse_and_marks_input_barrier():
    """拖动失败也必须释放鼠标并撤销旧视觉证明。"""
    q = Quartz(fail="drag")
    session = Session(q)
    with pytest.raises(RuntimeError):
        MacOSWindowInputDevice(session).drag_to(Point(105, 206), Point(110, 210))
    assert [e["kind"] for _, e in q.events] == ["move", "down", "drag", "up"]
    assert session.finished == 1


def test_click_holds_down_for_game_polling_before_release():
    """点击按住50毫秒，让轮询式游戏有机会观察到按下状态。"""
    q = Quartz()
    session = Session(q)
    now = [1.0]
    stamps = []
    original = q.CGEventPost

    def post(pid, event):
        """记录事件的单调时间。"""
        original(pid, event)
        stamps.append((event["kind"], now[0]))

    def sleep(amount):
        """以确定性时间执行有界按住。"""
        now[0] += amount

    q.CGEventPost = post
    MacOSWindowInputDevice(session, clock=lambda: now[0], sleep=sleep).click(
        Point(105, 206)
    )
    assert stamps[2][1] - stamps[1][1] >= 0.05 - 1e-9


def test_activation_failure_posts_no_input():
    """无法确认固定进程成为前台时明确停止，不发送会话输入。"""
    q = Quartz()
    session = Session(q)
    device = MacOSWindowInputDevice(
        session, activation=lambda pid, check, clock, sleep: 999
    )
    with pytest.raises(RuntimeError, match="未成为前台"):
        device.click(Point(105, 206))
    assert q.events == []
    assert session.finished == 0


def test_activation_reuses_bound_pid_and_does_not_reselect_window():
    """激活只接收固定 PID，不进行标题或窗口重新选择。"""
    q = Quartz()
    calls = []

    def activate(pid, check, clock, sleep):
        """确认收到已绑定的进程。"""
        calls.append(pid)
        return pid

    MacOSWindowInputDevice(Session(q), activation=activate).click(Point(105, 206))
    assert calls == [42]
    assert all(tap == q.kCGSessionEventTap for tap, _ in q.events)


def test_mouse_constructor_uses_window_base_coordinates_and_bound_number():
    """NSEvent 携带固定窗口号及左下原点坐标，不把全局点直接传入。"""
    q = Quartz()
    MacOSWindowInputDevice(Session(q)).click(Point(105, 206))
    assert [event["window-point"] for _, event in q.events] == [(5, 54)] * 3
    assert [event["point"] for _, event in q.events] == [(105, 206)] * 3
    assert [event["window-number"] for _, event in q.events] == [7] * 3
    assert [event["event-number"] for _, event in q.events] == [1, 2, 3]


def test_foreground_loss_after_activation_sends_no_mouse_down():
    """激活结果不能代替实际发送前的前台检查。"""
    q = Quartz()
    session = Session(q)
    device = MacOSWindowInputDevice(session, frontmost_pid=lambda: 999)
    with pytest.raises(RuntimeError, match="失焦"):
        device.click(Point(105, 206))
    assert q.events == []


def test_visible_floating_overlay_prevents_mouse_down():
    """有色浮层即使不属于普通窗口层，也不能被过滤后误点击。"""
    q = Quartz()
    q.rows.insert(
        0,
        {
            "number": 99,
            "alpha": 0.5,
            "layer": 50,
            "bounds": {"X": 100, "Y": 200, "Width": 80, "Height": 60},
        },
    )
    session = Session(q)
    with pytest.raises(RuntimeError, match="遮挡"):
        MacOSWindowInputDevice(session).click(Point(105, 206))
    assert [event["kind"] for _, event in q.events] == ["move"]
    assert session.finished == 1


def test_fully_transparent_overlay_is_not_a_visible_hit():
    """透明窗口不挡住目标命中，前后顺序仍由系统列表决定。"""
    q = Quartz()
    q.rows.insert(
        0,
        {
            "number": 99,
            "alpha": 0,
            "bounds": {"X": 100, "Y": 200, "Width": 80, "Height": 60},
        },
    )
    MacOSWindowInputDevice(Session(q)).click(Point(105, 206))
    assert [event["kind"] for _, event in q.events] == ["move", "down", "up"]


def test_mouse_up_is_released_even_if_focus_changes_after_down():
    """按下已经尝试发送后，失焦不能阻止必要的释放。"""
    q = Quartz()
    focused = [42]
    original = q.CGEventPost

    def post(tap, event):
        """模拟按下发送后前台被用户切走。"""
        original(tap, event)
        if event["kind"] == "down":
            focused[0] = 999

    q.CGEventPost = post
    MacOSWindowInputDevice(Session(q), frontmost_pid=lambda: focused[0]).click(
        Point(105, 206)
    )
    assert [event["kind"] for _, event in q.events] == ["move", "down", "up"]


def test_hotkey_loss_of_focus_prevents_subsequent_key_down_and_releases():
    """组合键中途失焦不再按下后续键，但已有修饰键必须释放。"""
    q = Quartz()
    focused = [42]
    original = q.CGEventPost

    def post(tap, event):
        """在修饰键按下后切换前台。"""
        original(tap, event)
        if event["kind"] == (55, True):
            focused[0] = 999

    q.CGEventPost = post
    with pytest.raises(RuntimeError, match="失焦"):
        MacOSWindowInputDevice(Session(q), frontmost_pid=lambda: focused[0]).hotkey(
            ("command", "a")
        )
    assert (0, True) not in [event["kind"] for _, event in q.events]
    assert [event["kind"] for _, event in q.events] == [(55, True), (55, False)]


def test_transport_is_explicit_in_user_log():
    """日志明确固定前台会话投递，不能把它描述成 PID 定向输入。"""
    q = Quartz()
    session = Session(q)
    messages = []
    session.logger = SimpleNamespace(log=messages.append)
    MacOSWindowInputDevice(session).click(Point(105, 206))
    assert any("input transport=foreground-session" in message for message in messages)
    assert all("PostToPid" not in message for message in messages)


def test_system_cursor_layer_is_not_an_interactive_covering_window():
    """系统光标刚移动到点击点时，公开光标层不应遮挡真正目标。"""
    q = Quartz()
    q.rows.insert(
        0,
        {
            "number": 2,
            "alpha": 1,
            "layer": 2147483630,
            "owner": "Window Server",
            "name": "Cursor",
            "bounds": {"X": 100, "Y": 200, "Width": 70, "Height": 101},
        },
    )
    MacOSWindowInputDevice(Session(q)).click(Point(105, 206))
    assert [event["kind"] for _, event in q.events] == ["move", "down", "up"]


def test_other_high_layer_visible_overlay_still_blocks_click():
    """只排除公开光标层，其他高层可见浮窗仍阻断鼠标按下。"""
    q = Quartz()
    q.rows.insert(
        0,
        {
            "number": 99,
            "alpha": 1,
            "layer": 2147483629,
            "bounds": {"X": 100, "Y": 200, "Width": 80, "Height": 60},
        },
    )
    with pytest.raises(RuntimeError, match="遮挡"):
        MacOSWindowInputDevice(Session(q)).click(Point(105, 206))
    assert "down" not in [event["kind"] for _, event in q.events]


class ActivationClock:
    def __init__(self):
        """建立不等待真实时钟的激活期限。"""
        self.now = 1.0

    def __call__(self):
        """读取单调时间。"""
        return self.now

    def sleep(self, amount):
        """推进一次激活轮询。"""
        self.now += amount


def install_activation_frameworks(
    monkeypatch, *, foreground, ax_error=0, terminated=False, missing=False
):
    """安装只按固定 PID 请求前台的轻量 AppKit/AX 边界。"""
    import sys

    calls = []
    pids = list(foreground)

    def frontmost():
        """模拟系统后续实际生效的前台状态。"""
        pid = pids.pop(0) if len(pids) > 1 else pids[0]
        return SimpleNamespace(processIdentifier=lambda: pid)

    def create_application(pid):
        """只接受绑定进程，不按名称查找应用。"""
        calls.append(("create", pid))
        return SimpleNamespace(pid=pid)

    def set_attribute(application, attribute, value):
        """记录应用级 frontmost 请求和系统错误码。"""
        calls.append(("set", application.pid, attribute, value))
        return ax_error

    app = None if missing else SimpleNamespace(isTerminated=lambda: terminated)
    appkit = SimpleNamespace(
        NSRunningApplication=SimpleNamespace(
            runningApplicationWithProcessIdentifier_=lambda pid: app
        ),
        NSWorkspace=SimpleNamespace(
            sharedWorkspace=lambda: SimpleNamespace(frontmostApplication=frontmost)
        ),
    )
    accessibility = SimpleNamespace(
        AXUIElementCreateApplication=create_application,
        AXUIElementSetAttributeValue=set_attribute,
        kAXFrontmostAttribute="frontmost",
        kAXErrorSuccess=0,
    )
    monkeypatch.setitem(sys.modules, "AppKit", appkit)
    monkeypatch.setitem(sys.modules, "ApplicationServices", accessibility)
    return calls


def test_already_foreground_requires_no_ax_request(monkeypatch):
    """已是绑定前台进程时直接通过，不再请求激活。"""
    calls = install_activation_frameworks(monkeypatch, foreground=(42,))
    clock = ActivationClock()
    assert activate_bound_application(42, lambda: None, clock, clock.sleep) == 42
    assert calls == []


def test_ax_activation_uses_bound_pid_and_waits_for_real_frontmost(monkeypatch):
    """只设置绑定 PID 的 frontmost，再以真实前台状态验收。"""
    calls = install_activation_frameworks(monkeypatch, foreground=(999, 999, 42))
    clock = ActivationClock()
    assert activate_bound_application(42, lambda: None, clock, clock.sleep) == 42
    assert calls == [("create", 42), ("set", 42, "frontmost", True)]


def test_ax_failure_retains_error_and_sends_no_input(monkeypatch):
    """AX明确拒绝时保留系统错误码，不尝试其他激活方式。"""
    calls = install_activation_frameworks(
        monkeypatch, foreground=(999,), ax_error=-25205
    )
    clock = ActivationClock()
    q = Quartz()
    with pytest.raises(RuntimeError, match="ax_error=-25205"):
        MacOSWindowInputDevice(
            Session(q),
            activation=activate_bound_application,
            clock=clock,
            sleep=clock.sleep,
        ).click(Point(105, 206))
    assert calls == [("create", 42), ("set", 42, "frontmost", True)]
    assert q.events == []


def test_successful_ax_request_without_real_focus_fails_before_events(monkeypatch):
    """AX请求成功不能证明生效，持续失焦时不发送输入。"""
    calls = install_activation_frameworks(monkeypatch, foreground=(999,), ax_error=0)
    clock = ActivationClock()
    q = Quartz()
    with pytest.raises(RuntimeError, match="激活超时") as caught:
        MacOSWindowInputDevice(
            Session(q),
            activation=activate_bound_application,
            clock=clock,
            sleep=clock.sleep,
        ).click(Point(105, 206))
    assert "ax_error=0" in str(caught.value)
    assert "frontmost_pid=999" in str(caught.value)
    assert calls == [("create", 42), ("set", 42, "frontmost", True)]
    assert q.events == []


@pytest.mark.parametrize("missing", [False, True])
def test_exited_process_is_rejected_even_with_stale_frontmost_pid(monkeypatch, missing):
    """进程退出或不存在时，不能用过期前台 PID 继续输入。"""
    calls = install_activation_frameworks(
        monkeypatch, foreground=(42,), terminated=True, missing=missing
    )
    clock = ActivationClock()
    with pytest.raises(RuntimeError, match="已经退出"):
        activate_bound_application(42, lambda: None, clock, clock.sleep)
    assert calls == []


@pytest.mark.parametrize(
    "title,rect",
    [
        ("Other", Rect(100, 200, 80, 60)),
        ("Game", Rect(101, 200, 80, 60)),
        ("Game", Rect(100, 200, 81, 60)),
    ],
)
def test_same_pid_other_focused_window_prevents_all_key_down(title, rect):
    """同一前台应用的其他标题或几何窗口也不能接收按键。"""
    from game_automation.portable.application.ports import FocusedApplicationWindow

    q = Quartz()
    device = MacOSWindowInputDevice(
        Session(q), keyboard_focus=lambda pid: FocusedApplicationWindow(title, rect)
    )
    with pytest.raises(RuntimeError, match="焦点窗口"):
        device.hotkey(("command", "a"))
    assert q.events == []


def test_focus_window_change_releases_only_attempted_modifier():
    """同PID焦点窗口切换后，不发第二键的down或从未尝试的up。"""
    from game_automation.portable.application.ports import FocusedApplicationWindow

    q = Quartz()
    focus = [
        FocusedApplicationWindow("Game", Rect(100, 200, 80, 60)),
        FocusedApplicationWindow("Other", Rect(100, 200, 80, 60)),
    ]
    calls = []

    def read(pid):
        """只读绑定应用当前焦点窗口，不重新选择。"""
        calls.append(pid)
        return focus.pop(0)

    with pytest.raises(RuntimeError, match="焦点窗口"):
        MacOSWindowInputDevice(Session(q), keyboard_focus=read).hotkey(("command", "a"))
    assert calls == [42, 42]
    assert [event["kind"] for _, event in q.events] == [(55, True), (55, False)]
