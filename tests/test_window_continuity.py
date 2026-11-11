"""验证后台会话暂停恢复、任务时钟与点击准备的可观察行为。

系统窗口、窗口流和时间均使用替身；不证明真实游戏或调度中心已兼容。
"""
from types import SimpleNamespace

from PIL import Image
import pytest

from game_automation.platform.macos.adapters.window_runtime import MacOSWindowSession
from game_automation.portable.application.capture_errors import WindowCaptureError
from game_automation.portable.application.window_state_rules import WindowStateRules
from game_automation.portable.domain import AreaWindow, Click, ImageMatch, ImageTarget, ImageTemplate, Point, Rect, Script
from game_automation.portable.domain.screen_state import FrameProof
from game_automation.portable.engine.cancellation import ScriptCancelledError
from game_automation.portable.engine.runner import ScriptRunner
from game_automation.portable.preparation.models import DesktopWindow


class Clock:
    def __init__(self):
        """保存可推进的系统时间。"""
        self.now = 10.0
        self.on_sleep = lambda: None
    def __call__(self):
        """返回真实时间替身。"""
        return self.now
    def sleep(self, seconds):
        """推进时间并允许系统状态恢复。"""
        self.now += seconds
        self.on_sleep()


class Binding:
    def __init__(self, window):
        """保存唯一身份和当前窗口几何。"""
        self.window, self.number = window, 7
        self.quartz = SimpleNamespace(kCGWindowBounds='bounds')
        self.bounds = {'X':100, 'Y':200, 'Width':80, 'Height':60}
        self.error = None
    def check(self):
        """返回当前系统状态或身份错误。"""
        if self.error:
            raise self.error
        return {'bounds':self.bounds}


class Source:
    def __init__(self, clock):
        """提供与系统时间一致的真实新事件替身。"""
        self.clock, self.proof = clock, None
        self.error = None
        self.sequence = 0
        self.closed = False
    def check_available(self):
        """返回新的有效源事件或指定采集错误。"""
        if self.error:
            raise self.error
        self.sequence += 1
        return FrameProof(self.sequence, self.clock())
    def screenshot(self):
        """将像素与同轮源证明一并交付。"""
        self.proof = self.check_available()
        return Image.new('RGB', (160, 120))
    def close(self):
        """记录源已释放。"""
        self.closed = True


def setup(source_factory=None):
    """装配独立后台会话及可注入的系统边界。"""
    window = DesktopWindow('42:7', 'Game', '页面', Rect(100, 200, 80, 60))
    clock, messages = Clock(), []
    binding = Binding(window)
    session = MacOSWindowSession(window, binding, WindowStateRules((), 80, 60, 160, 120),
        backend='macos-window-background', clock=clock, sleep=clock.sleep,
        logger=SimpleNamespace(log=messages.append))
    source = Source(clock) if source_factory is None else source_factory(window, binding, clock)
    session.attach_source(source)
    return session, binding, source, clock, messages


def test_background_move_waits_for_original_geometry_and_fresh_proof():
    """短暂窗口变化恢复后返回新画面，任务时间不包含暂停。"""
    session, binding, source, clock, messages = setup()
    binding.bounds['X'] = 101
    def restore():
        """半秒后恢复原始几何。"""
        if clock() >= 10.5:
            binding.bounds['X'] = 100
    clock.on_sleep = restore
    with session.screenshot() as image:
        assert image.size == (160, 120)
    assert clock() >= 10.5
    assert session.task_time() < 10.1
    assert source.proof.captured_at > 10.5
    assert sum('runtime paused' in message for message in messages) == 1
    assert sum('runtime resumed' in message for message in messages) == 1


def test_cancel_while_waiting_preserves_owned_source_cleanup():
    """持续窗口变化时取消立即生效，源仍由会话关闭。"""
    session, binding, source, clock, _ = setup()
    binding.bounds['Width'] = 81
    session.cancellation = SimpleNamespace(is_cancelled=lambda: clock() >= 10.1)
    with pytest.raises(ScriptCancelledError):
        session.check_window()
    session.close()
    assert source.closed
    assert clock() < 10.2


def test_terminal_identity_failure_is_never_waited_or_rebound():
    """真实窗口替换仍明确失败。"""
    session, binding, _, clock, _ = setup()
    binding.error = WindowCaptureError('window replaced')
    with pytest.raises(WindowCaptureError, match='replaced'):
        session.check_window()
    assert clock() == 10


def test_image_click_resolves_again_after_pre_dispatch_pause():
    """定位后窗口变化时丢弃旧点位，恢复后只发送新点位一次。"""
    session, binding, _, clock, _ = setup()
    sent, reads = [], []
    class Locator:
        def locate(self, template, **kwargs):
            """第一轮定位后模拟窗口变化，第二轮返回新目标。"""
            reads.append(1)
            if len(reads) == 1:
                binding.bounds['X'] = 101
                return ImageMatch(Rect(105, 206, 2, 2), 1)
            return ImageMatch(Rect(120, 220, 2, 2), 1)
    class Device:
        def click(self, point):
            """只在最终校验成功后执行外部副作用。"""
            session.check_window()
            session.commit_input()
            sent.append(point)
    def restore():
        """系统在等待时恢复原矩形。"""
        binding.bounds['X'] = 100
    clock.on_sleep = restore
    script = Script('image', AreaWindow(Rect(100, 200, 80, 60)), (Click(ImageTarget(ImageTemplate('unused.png'))),))
    runner = ScriptRunner(Device(), image_locator=Locator(), runtime_control=session)
    assert runner.run(script).finish_reason == 'completed'
    assert len(reads) == 2
    assert sent == [Point(121, 221)]


def test_post_dispatch_pause_never_replays_action():
    """已尝试按下后出现短暂变化，只等待恢复并返回原结果。"""
    session, binding, _, clock, _ = setup()
    sent = []
    def action():
        """在已提交区模拟外部副作用及窗口变化。"""
        session.commit_input()
        sent.append('down/up')
        binding.bounds['X'] = 101
        session.check_window()
        return 'done'
    clock.on_sleep = lambda: binding.bounds.update(X=100)
    assert session.execute_input(action) == 'done'
    assert sent == ['down/up']


def test_stream_presentation_pause_recovers_but_stop_remains_terminal():
    """采集暂态可恢复，系统真正停流仍失败。"""
    from game_automation.platform.macos.adapters.window_identity import WindowPresentationUnavailable
    session, _, source, clock, _ = setup()
    source.error = WindowPresentationUnavailable('暂时暂停')
    clock.on_sleep = lambda: setattr(source, 'error', None)
    session.check_window()
    assert session.task_time() < 10.1
    source.error = WindowCaptureError('stream stopped')
    with pytest.raises(WindowCaptureError, match='stopped'):
        session.check_window()


def test_ordinary_wait_excludes_presentation_pause():
    """普通等待在暂停后继续剩余有效时间。"""
    from game_automation.platform.macos.adapters.window_background_input import MacOSBackgroundWindowInputDevice
    session, binding, _, clock, _ = setup()
    adapter = MacOSBackgroundWindowInputDevice(session, window_location_setter=lambda *args: None,
        frontmost_pid=lambda:999, clock=clock, sleep=clock.sleep)
    binding.bounds['X'] = 101
    def restore():
        """系统时间过半秒才结束暂停。"""
        if clock() >= 10.5:
            binding.bounds['X'] = 100
    clock.on_sleep = restore
    adapter.wait(0.1)
    assert clock() >= 10.6
    assert session.task_time() == pytest.approx(10.1)


def test_recovery_requires_later_source_time_and_sequence():
    """恢复时读取同一个旧缓存不能冒充新画面。"""
    session, binding, source, clock, _ = setup()
    source.proof = FrameProof(7, 9.99)
    reads = []
    def capture():
        """先重复旧证明，半秒后再发布恢复后的新事件。"""
        reads.append(clock())
        if clock() >= 10.5:
            source.proof = FrameProof(8, clock())
        return Image.new('RGB', (160, 120))
    source.screenshot = capture
    source.check_available = lambda: source.proof
    binding.bounds['X'] = 101
    clock.on_sleep = lambda: binding.bounds.update(X=100)
    session.check_window()
    assert clock() >= 10.5
    assert len(reads) > 1
    assert source.proof.sequence == 8


def test_recovery_during_image_guard_restarts_target_preparation():
    """定位后的守卫遇到暂停也必须重新定位，不能发送旧目标。"""
    session, binding, _, clock, _ = setup()
    sent, reads, guards = [], [], []
    class Locator:
        def locate(self, template, **kwargs):
            """每次定位提供不同位置以检验是否重做。"""
            reads.append(1)
            return ImageMatch(Rect(100 + len(reads)*10, 210, 2, 2), 1)
    class Device:
        def click(self, point):
            """提交唯一一次点击。"""
            session.commit_input()
            sent.append(point)
    def guard():
        """第一轮守卫触发窗口变化，恢复后重新核对。"""
        guards.append(1)
        if len(guards) == 1:
            binding.bounds['X'] = 101
        session.check_window()
    clock.on_sleep = lambda: binding.bounds.update(X=100)
    script = Script('guard', AreaWindow(Rect(100, 200, 80, 60)), (Click(ImageTarget(ImageTemplate('unused.png'))),))
    runner = ScriptRunner(Device(), image_locator=Locator(), runtime_control=session, _step_guard=guard)
    runner.run(script)
    assert sent == [Point(121, 211)]
    assert len(reads) == 2


def test_another_transition_immediately_after_resume_keeps_waiting():
    """恢复瞬间再次发生展示变化仍等待，暂态不会逃逸为失败。"""
    session, binding, _, clock, messages = setup()
    resumes = []
    def log(message):
        """模拟恢复通知发出时系统再次开始动画。"""
        messages.append(message)
        if 'runtime resumed' in message:
            resumes.append(1)
            if len(resumes) == 1:
                binding.bounds['X'] = 102
    session.logger = SimpleNamespace(log=log)
    binding.bounds['X'] = 101
    clock.on_sleep = lambda: binding.bounds.update(X=100)
    session.check_window()
    assert binding.bounds['X'] == 100
    assert len(resumes) == 2


def test_move_during_first_frame_wait_recovers_using_full_session_geometry():
    """首帧等待期间仅原点变化，也按会话原矩形恢复。"""
    from game_automation.platform.macos.adapters.window_stream import LatestWindowFrame, StreamPixels, WindowStreamSource
    with pytest.raises(WindowCaptureError) as pending:
        LatestWindowFrame().take(0)
    slots = []
    class Driver:
        def start(self, binding, size, hz, slot):
            """模拟等待首帧时窗口发生原点变化。"""
            slots.append(slot)
            take = slot.take
            def first_wait():
                """保持身份和尺寸，只改变位置后结束无帧等待。"""
                slot.take = take
                binding.bounds['X'] = 101
                raise pending.value
            slot.take = first_wait
        def close(self):
            """无需关闭真实系统资源。"""
    def source_factory(window, binding, clock):
        """通过公开装配边界提供可控首帧的窗口源。"""
        return WindowStreamSource(window, (160,120), binding=binding, driver_factory=Driver)
    session, binding, source, clock, messages = setup(source_factory)
    def restore():
        """恢复位置并持续交付真实时间推进的新帧。"""
        binding.bounds['X'] = 100
        slots[0].publish('complete', clock(), StreamPixels(bytes(160*120*4),160,120,160*4))
    clock.on_sleep = restore
    try:
        session.check_window()
        assert binding.bounds['X'] == 100
        assert source.proof is not None
        assert sum('runtime resumed' in message for message in messages) == 1
    finally:
        session.close()
