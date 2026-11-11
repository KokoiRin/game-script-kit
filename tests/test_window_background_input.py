"""验证显式后台点击试验的PID投递、坐标、私有依赖及释放边界。"""
from types import SimpleNamespace

import pytest

from game_automation.platform.macos.adapters.window_background_input import MacOSBackgroundWindowInputDevice
from game_automation.portable.domain import Point, Rect


class AppKit:
    NSEventTypeMouseMoved = 'move'
    NSEventTypeLeftMouseDown = 'down'
    NSEventTypeLeftMouseUp = 'up'
    class NSEvent:
        @staticmethod
        def mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(kind, point, flags, stamp, number, context, event_number, count, pressure):
            """返回已有窗口关联字段的NSEvent替身。"""
            return SimpleNamespace(CGEvent=lambda: {'kind':kind, 'window-base':point, 'window-number':number})


class Quartz:
    kCGEventMouseMoved = 'move'
    kCGEventLeftMouseDown = 'down'
    kCGEventLeftMouseUp = 'up'
    kCGMouseEventButtonNumber = 3
    kCGMouseEventSubtype = 7
    kCGMouseEventClickState = 1
    kCGMouseEventWindowUnderMousePointer = 91
    kCGMouseEventWindowUnderMousePointerThatCanHandleThisEvent = 92
    def __init__(self, fail=None):
        """仅提供PID投递；缺少全局投递API确保无法误用。"""
        self.events = []
        self.fail = fail
    def CGEventSetLocation(self, event, point):
        """设置事件坐标，不移动真实指针。"""
        event['global'] = point
    def CGEventGetLocation(self, event):
        """返回公开setter后的全局点。"""
        return event['global']
    def CGEventSetIntegerValueField(self, event, field, value):
        """保存明确字段。"""
        event[field] = value
    def CGEventSetFlags(self, event, flags):
        """保存后台command位。"""
        event['flags'] = flags
    def CGEventPostToPid(self, pid, event):
        """记录唯一transport并模拟投递后抛错。"""
        self.events.append((pid, event))
        if self.fail == event['kind']:
            raise RuntimeError('post failed')


class Session:
    def __init__(self, quartz):
        """给出固定PID、CG窗口和屏幕原点。"""
        self.binding = SimpleNamespace(quartz=quartz, number=7)
        self.window = SimpleNamespace(id='42:1', title='Game', rect=Rect(100, 200, 80, 60))
        self.finished = 0
        self.messages = []
        self.logger = SimpleNamespace(log=self.messages.append)
    def check_window(self):
        """模拟已有身份与取消校验。"""
    def check_cancelled(self):
        """默认没有取消请求。"""
    def commit_input(self):
        """投递边界由真实会话负责，此替身只记录外部事件。"""
    def validate_point(self, point):
        """仅允许固定窗口内部点。"""
        assert 100 <= point.x < 180 and 200 <= point.y < 260
    def input_finished(self):
        """撤销输入前的视觉证明。"""
        self.finished += 1


def device(session, *, frontmost=999):
    """注入私有事件字段setter，不调用任何真实平台能力。"""
    now = [1.0]
    def sleep(amount):
        """推进虚拟按住时间。"""
        now[0] += amount
    def local_setter(event, point):
        """记录窗口左上相对坐标。"""
        event['window-local'] = point
    return MacOSBackgroundWindowInputDevice(session, appkit=AppKit, window_location_setter=local_setter,
                                            frontmost_pid=frontmost if callable(frontmost) else lambda: frontmost, clock=lambda: now[0], sleep=sleep)


def test_background_recipe_posts_only_to_pid_with_complete_fields():
    """同一绑定窗口依次收到primer/down/up和完整后台字段。"""
    q = Quartz()
    session = Session(q)
    device(session).click(Point(105, 206))
    assert [event['kind'] for _, event in q.events] == ['move', 'down', 'up']
    for pid, event in q.events:
        assert pid == 42
        assert event['window-number'] == 7
        assert event['window-base'] == (5, 54)
        assert event['global'] == (105, 206)
        assert event['window-local'] == (5, 6)
        assert (event[3], event[7], event[91], event[92]) == (0, 3, 7, 7)
        assert event['flags'] == 0x100000
    assert session.finished == 1
    assert any('frontmost_pid=999' in message and 'background-pid-experiment' in message for message in session.messages)


def test_foreground_game_uses_the_same_pid_transport():
    """目标在前台时仍通过固定PID完成一次点击。"""
    q = Quartz()
    device(Session(q), frontmost=42).click(Point(105, 206))
    assert [(pid, event['kind']) for pid, event in q.events] == [(42, 'move'), (42, 'down'), (42, 'up')]


def test_down_post_failure_still_releases_and_invalidates_old_frame():
    """PID投递可能先发出再报错，仍必须配对up。"""
    q = Quartz(fail='down')
    session = Session(q)
    with pytest.raises(RuntimeError, match='post failed'):
        device(session).click(Point(105, 206))
    assert [event['kind'] for _, event in q.events] == ['move', 'down', 'up']
    assert session.finished == 1


def test_keyboard_and_drag_are_explicitly_unsupported():
    """未经实测的后台输入能力不默认为可用。"""
    q = Quartz()
    adapter = device(Session(q))
    with pytest.raises(NotImplementedError):
        adapter.hotkey(('command', 'a'))
    with pytest.raises(NotImplementedError):
        adapter.drag_to(Point(105, 206), Point(110, 210))
    assert q.events == []


def test_missing_private_setter_fails_before_any_event(monkeypatch):
    """私有依赖缺失必须显式失败，不启用另一种输入transport。"""
    from game_automation.platform.macos.adapters import window_background_input as module
    def unavailable():
        """模拟当前系统没有私有符号。"""
        raise RuntimeError('CGEventSetWindowLocation unavailable')
    monkeypatch.setattr(module, 'load_window_location_setter', unavailable)
    q = Quartz()
    with pytest.raises(RuntimeError, match='CGEventSetWindowLocation'):
        module.MacOSBackgroundWindowInputDevice(Session(q), appkit=AppKit, frontmost_pid=lambda: 999)
    assert q.events == []


def test_cancelled_hold_releases_without_rechecking_cancellation():
    """后台按住期间取消，必要释放不再被取消校验阻断。"""
    from game_automation.portable.engine.cancellation import ScriptCancelledError
    q = Quartz()
    session = Session(q)
    def check():
        """收到按下后模拟协作取消。"""
        if any(event['kind'] == 'down' for _, event in q.events):
            raise ScriptCancelledError('cancelled')
    session.check_cancelled = check
    with pytest.raises(ScriptCancelledError):
        device(session).click(Point(105, 206))
    assert [event['kind'] for _, event in q.events] == ['move', 'down', 'up']
    assert session.finished == 1


def test_release_does_not_depend_on_frontmost_read_after_down():
    """按下后前台读取出错，也必须发送配对up，日志可使用已确认缓存。"""
    q = Quartz()
    session = Session(q)
    def read_frontmost():
        """模拟down之后系统查询暂时抛错。"""
        if any(event['kind'] == 'down' for _, event in q.events):
            raise RuntimeError('frontmost read failed')
        return 999
    device(session, frontmost=read_frontmost).click(Point(105, 206))
    assert [event['kind'] for _, event in q.events] == ['move', 'down', 'up']
    assert session.finished == 1
