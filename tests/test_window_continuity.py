"""验证后台会话暂停恢复、任务时钟与点击准备的可观察行为。

系统窗口、窗口流和时间均使用替身；不证明真实游戏或调度中心已兼容。
"""

from types import SimpleNamespace

import pytest
from PIL import Image

from game_automation.platform.macos.adapters.window_runtime import MacOSWindowSession
from game_automation.portable.application.capture_errors import WindowCaptureError
from game_automation.portable.application.window_state_rules import WindowStateRules
from game_automation.portable.domain import (
    AreaWindow,
    ImageMatch,
    ImageTarget,
    ImageTemplate,
    Point,
    Rect,
)
from game_automation.portable.domain.screen_state import FrameProof
from game_automation.portable.engine.cancellation import TaskCancelledError
from game_automation.portable.preparation.models import DesktopWindow
from game_automation.task import TaskContext
from tests.support.function_tasks import function_task


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
        self.quartz = SimpleNamespace(kCGWindowBounds="bounds")
        self.bounds = {"X": 100, "Y": 200, "Width": 80, "Height": 60}
        self.error = None

    def check(self):
        """返回当前系统状态或身份错误。"""
        if self.error:
            raise self.error
        return {"bounds": self.bounds}


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
        return Image.new("RGB", (160, 120))

    def close(self):
        """设置可观察的关闭标记，供测试确认恢复或取消之后采集源仍被回收。"""
        self.closed = True


def setup(source_factory=None):
    """装配独立后台会话及可注入的系统边界。"""
    window = DesktopWindow("42:7", "Game", "页面", Rect(100, 200, 80, 60))
    clock, messages = Clock(), []
    binding = Binding(window)
    session = MacOSWindowSession(
        window,
        binding,
        WindowStateRules((), 80, 60, 160, 120),
        backend="macos-window-background",
        clock=clock,
        sleep=clock.sleep,
        logger=SimpleNamespace(log=messages.append),
    )
    source = (
        Source(clock)
        if source_factory is None
        else source_factory(window, binding, clock)
    )
    session.attach_source(source)
    return session, binding, source, clock, messages


def test_background_move_adopts_new_geometry_and_fresh_proof():
    """平移后在新位置继续，暂停只包含稳定和新画面等待。"""
    session, binding, source, clock, messages = setup()
    binding.bounds["X"] = 301
    with session.screenshot() as image:
        assert image.size == (160, 120)
    assert session.rect == Rect(301, 200, 80, 60)
    assert binding.bounds["X"] == 301
    assert clock() < 10.1
    assert session.task_time() == 10
    assert source.proof.captured_at > 10
    assert sum("runtime paused" in message for message in messages) == 1
    assert sum("runtime resumed" in message for message in messages) == 1


def test_cancel_while_waiting_preserves_owned_source_cleanup():
    """持续窗口变化时取消立即生效，源仍由会话关闭。"""
    session, binding, source, clock, _ = setup()
    binding.bounds["Width"] = 81
    session.cancellation = SimpleNamespace(is_cancelled=lambda: clock() >= 10.1)
    with pytest.raises(TaskCancelledError):
        session.check_window()
    session.close()
    assert source.closed
    assert clock() < 10.2


def test_terminal_identity_failure_is_never_waited_or_rebound():
    """真实窗口替换仍明确失败。"""
    session, binding, _, clock, _ = setup()
    binding.error = WindowCaptureError("window replaced")
    with pytest.raises(WindowCaptureError, match="replaced"):
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
                binding.bounds["X"] = 101
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
        binding.bounds["X"] = 100

    clock.on_sleep = restore
    script = function_task(
        "image",
        "ctx.click(ImageTarget(ImageTemplate('unused.png')))",
        window=AreaWindow(Rect(100, 200, 80, 60)),
        templates=(ImageTemplate("unused.png"),),
    )
    context = TaskContext(
        script.window,
        script.resources,
        device=Device(),
        image_locator=Locator(),
        runtime_control=session,
    )
    context.click(ImageTarget(ImageTemplate("unused.png")))
    assert len(reads) == 2
    assert sent == [Point(121, 221)]


def test_post_dispatch_pause_never_replays_action():
    """已尝试按下后出现短暂变化，只等待恢复并返回原结果。"""
    session, binding, _, clock, _ = setup()
    sent = []

    def action():
        """在已提交区模拟外部副作用及窗口变化。"""
        session.commit_input()
        sent.append("down/up")
        binding.bounds["X"] = 101
        session.check_window()
        return "done"

    clock.on_sleep = lambda: binding.bounds.update(X=100)
    assert session.execute_input(action) == "done"
    assert sent == ["down/up"]


def test_stream_presentation_pause_recovers_but_stop_remains_terminal():
    """采集暂态可恢复，系统真正停流仍失败。"""
    from game_automation.platform.macos.adapters.window_identity import (
        WindowPresentationUnavailable,
    )

    session, _, source, clock, _ = setup()
    source.error = WindowPresentationUnavailable("暂时暂停")
    clock.on_sleep = lambda: setattr(source, "error", None)
    session.check_window()
    assert session.task_time() < 10.1
    source.error = WindowCaptureError("stream stopped")
    with pytest.raises(WindowCaptureError, match="stopped"):
        session.check_window()


def test_ordinary_wait_excludes_presentation_pause():
    """普通等待在暂停后继续剩余有效时间。"""
    from game_automation.platform.macos.adapters.window_background_input import (
        MacOSBackgroundWindowInputDevice,
    )

    session, binding, _, clock, _ = setup()
    adapter = MacOSBackgroundWindowInputDevice(
        session,
        window_location_setter=lambda *args: None,
        frontmost_pid=lambda: 999,
        clock=clock,
        sleep=clock.sleep,
    )
    binding.bounds["Width"] = 81

    def restore():
        """尺寸变化仍需要恢复素材尺寸，平移位置无需还原。"""
        if clock() >= 10.5:
            binding.bounds.update(Width=80, X=301)

    clock.on_sleep = restore
    adapter.wait(0.1)
    assert clock() >= 10.6
    assert session.rect.left == 301
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
        return Image.new("RGB", (160, 120))

    source.screenshot = capture
    source.check_available = lambda: source.proof
    binding.bounds["X"] = 101
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
            return ImageMatch(Rect(100 + len(reads) * 10, 210, 2, 2), 1)

    class Device:
        def click(self, point):
            """提交唯一一次点击。"""
            session.commit_input()
            sent.append(point)

    def guard():
        """第一轮守卫触发窗口变化，恢复后重新核对。"""
        guards.append(1)
        if len(guards) == 1:
            binding.bounds["X"] = 101
        session.check_window()

    clock.on_sleep = lambda: binding.bounds.update(X=100)
    script = function_task(
        "guard",
        "ctx.click(ImageTarget(ImageTemplate('unused.png')))",
        window=AreaWindow(Rect(100, 200, 80, 60)),
        templates=(ImageTemplate("unused.png"),),
    )
    context = TaskContext(
        script.window,
        script.resources,
        device=Device(),
        image_locator=Locator(),
        runtime_control=session,
    )
    with context.scope(checkpoint=guard):
        context.click(ImageTarget(ImageTemplate("unused.png")))
    assert sent == [Point(121, 211)]
    assert len(reads) == 2


def test_another_transition_immediately_after_resume_keeps_waiting():
    """恢复瞬间再次发生展示变化仍等待，暂态不会逃逸为失败。"""
    session, binding, _, clock, messages = setup()
    resumes = []

    def log(message):
        """模拟恢复通知发出时系统再次开始动画。"""
        messages.append(message)
        if "runtime resumed" in message:
            resumes.append(1)
            if len(resumes) == 1:
                binding.bounds["X"] = 102

    session.logger = SimpleNamespace(log=log)
    binding.bounds["X"] = 101
    clock.on_sleep = lambda: binding.bounds.update(X=100)
    session.check_window()
    assert binding.bounds["X"] == 100
    assert len(resumes) == 2


def test_move_during_first_frame_wait_recovers_using_full_session_geometry():
    """首帧等待期间仅原点变化，也按会话原矩形恢复。"""
    from game_automation.platform.macos.adapters.window_stream import (
        LatestWindowFrame,
        StreamPixels,
        WindowStreamSource,
    )

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
                binding.bounds["X"] = 101
                raise pending.value

            slot.take = first_wait

        def close(self):
            """无需关闭真实系统资源。"""

    def source_factory(window, binding, clock):
        """通过公开装配边界提供可控首帧的窗口源。"""
        return WindowStreamSource(
            window, (160, 120), binding=binding, driver_factory=Driver
        )

    session, binding, source, clock, messages = setup(source_factory)

    def restore():
        """恢复位置并持续交付真实时间推进的新帧。"""
        binding.bounds["X"] = 100
        slots[0].publish(
            "complete", clock(), StreamPixels(bytes(160 * 120 * 4), 160, 120, 160 * 4)
        )

    clock.on_sleep = restore
    try:
        session.check_window()
        assert binding.bounds["X"] == 100
        assert source.proof is not None
        assert sum("runtime resumed" in message for message in messages) == 1
    finally:
        session.close()


def test_point_preparation_retries_at_new_origin_without_returning_to_old_position():
    """准备后平移会重新解析整个点位且只提交一次。"""
    from game_automation.platform.macos.adapters.window_runtime import SessionWindow

    session, binding, _, _, _ = setup()
    window = SessionWindow(session)
    attempts, sent = [], []

    def prepare():
        """模拟解析之后、最终提交之前平移。"""
        point = window.resolve(Point(5, 6))
        attempts.append(point)
        if len(attempts) == 1:
            binding.bounds.update(X=500, Y=600)
        session.validate_point(point)
        session.commit_input()
        sent.append(point)

    session.execute_input(prepare)
    assert attempts == [Point(105, 206), Point(505, 606)]
    assert sent == [Point(505, 606)]


def test_color_retries_resolution_when_window_moves_during_capture():
    """截图中途移动时重做局部点解析，取色不会混用两个原点。"""
    from game_automation.platform.macos.adapters.window_runtime import SessionWindow
    from game_automation.platform.macos.adapters.window_vision import WindowColorReader
    from game_automation.portable.domain import Color

    session, binding, source, _, _ = setup()
    capture = source.screenshot
    reads = []

    def screenshot():
        """首张画面触发移动，后续帧包含固定局部颜色。"""
        image = capture()
        reads.append(1)
        image.putpixel((10, 12), (21, 22, 23))
        if len(reads) == 1:
            binding.bounds.update(X=500, Y=600)
        return image

    source.screenshot = screenshot
    context = TaskContext(
        SessionWindow(session),
        function_task("color", "pass").resources,
        device=SimpleNamespace(),
        color_reader=WindowColorReader(session),
        runtime_control=session,
    )
    assert context.color(Point(5, 6)) == Color(21, 22, 23)
    assert len(reads) >= 3
    assert session.rect.left == 500


def test_roi_and_match_share_snapshot_after_observation_retries():
    """ROI及匹配结果整轮重试，原生适配器继续接收全局坐标。"""
    from game_automation.platform.macos.adapters.window_runtime import SessionWindow
    from game_automation.platform.macos.adapters.window_vision import WindowImageLocator

    session, binding, _, _, _ = setup()
    regions = []

    class Locator:
        def __init__(self, *, backend):
            """借用同一会话采集边界。"""
            self.backend = backend

        def locate(self, template, *, region, **kwargs):
            """定位期间移动，使外层观察丢弃旧结果。"""
            regions.append(region)
            if len(regions) == 1:
                binding.bounds.update(X=700, Y=800)
            with self.backend.screenshot():
                return ImageMatch(Rect(5, 6, 2, 2), 1)

    locator = WindowImageLocator(session, locator_factory=Locator)
    window = SessionWindow(session)
    result = session.execute_observation(
        lambda: locator.locate(
            ImageTemplate("unused.png"),
            region=window.resolve_region(Rect(1, 2, 30, 20)),
        )
    )
    assert regions == [Rect(1, 2, 30, 20), Rect(1, 2, 30, 20)]
    assert result.rect == Rect(705, 806, 2, 2)


def test_nested_observation_retries_whole_uncommitted_input():
    """输入内观察遇到平移时重新执行外层准备，避免部分坐标过期。"""
    from game_automation.platform.macos.adapters.window_runtime import SessionWindow

    session, binding, _, _, _ = setup()
    window, attempts, sent = SessionWindow(session), [], []

    def prepare():
        """保存先解析的点，再通过嵌套观察检测移动。"""
        point = window.resolve(Point(1, 2))
        attempts.append(point)

        def observe():
            """第一次嵌套读取触发新位置。"""
            if len(attempts) == 1:
                binding.bounds.update(X=500)
            session.check_window()

        session.execute_observation(observe)
        session.commit_input()
        sent.append(point)

    session.execute_input(prepare)
    assert attempts == [Point(101, 202), Point(501, 202)]
    assert sent == [Point(501, 202)]


def test_background_up_keeps_down_local_anchor_after_movement():
    """按下之后移动只释放原局部点，下一次点击使用新位置。"""
    from game_automation.platform.macos.adapters.window_background_input import (
        MacOSBackgroundWindowInputDevice,
    )
    from game_automation.platform.macos.adapters.window_runtime import SessionWindow
    from tests.test_window_background_input import AppKit, Quartz

    session, binding, _, clock, _ = setup()
    q = Quartz()
    q.kCGWindowBounds = "bounds"
    binding.quartz = q
    post = q.CGEventPostToPid

    def post_and_move(pid, event):
        """真实投递替身在按下后移动窗口。"""
        post(pid, event)
        if event["kind"] == "down":
            binding.bounds.update(X=500, Y=600)

    q.CGEventPostToPid = post_and_move
    device = MacOSBackgroundWindowInputDevice(
        session,
        appkit=AppKit,
        window_location_setter=lambda event, point: event.update(local=point),
        frontmost_pid=lambda: 42,
        clock=clock,
        sleep=clock.sleep,
    )
    window = SessionWindow(session)
    session.execute_input(lambda: device.click(window.resolve(Point(5, 6))))
    assert [e["kind"] for _, e in q.events] == ["move", "down", "up"]
    assert q.events[-1][1]["local"] == (5, 6)
    assert q.events[-1][1]["global"] == (505, 606)
    session.execute_input(lambda: device.click(window.resolve(Point(5, 6))))
    assert q.events[-2][1]["global"] == (505, 606)


def test_continuously_moving_window_remains_cancellable():
    """连续拖动稳定等待不会阻塞停止。"""
    session, binding, _, clock, _ = setup()
    binding.bounds.update(X=101)
    clock.on_sleep = lambda: binding.bounds.update(X=binding.bounds["X"] + 1)
    session.cancellation = SimpleNamespace(is_cancelled=lambda: clock() >= 10.1)
    with pytest.raises(TaskCancelledError):
        session.execute_observation(lambda: None)
    assert clock() < 10.2


def test_cancel_after_background_down_still_releases_at_moved_local_point():
    """移动后立即取消仍发送一次原局部点释放，不重放点击。"""
    from game_automation.platform.macos.adapters.window_background_input import (
        MacOSBackgroundWindowInputDevice,
    )
    from game_automation.platform.macos.adapters.window_runtime import SessionWindow
    from tests.test_window_background_input import AppKit, Quartz

    session, binding, _, clock, _ = setup()
    q, cancelled = Quartz(), []
    q.kCGWindowBounds = "bounds"
    binding.quartz = q
    session.cancellation = SimpleNamespace(is_cancelled=lambda: bool(cancelled))
    post = q.CGEventPostToPid

    def post_and_cancel(pid, event):
        """按下后立刻平移并收到停止请求。"""
        post(pid, event)
        if event["kind"] == "down":
            binding.bounds.update(X=500, Y=600)
            cancelled.append(True)

    q.CGEventPostToPid = post_and_cancel
    device = MacOSBackgroundWindowInputDevice(
        session,
        appkit=AppKit,
        window_location_setter=lambda event, point: event.update(local=point),
        frontmost_pid=lambda: 42,
        clock=clock,
        sleep=clock.sleep,
    )
    with pytest.raises(TaskCancelledError):
        session.execute_input(
            lambda: device.click(SessionWindow(session).resolve(Point(5, 6)))
        )
    assert [e["kind"] for _, e in q.events] == ["move", "down", "up"]
    assert q.events[-1][1]["local"] == (5, 6)
    assert q.events[-1][1]["global"] == (505, 606)


def test_foreground_hotkey_translation_preserves_pairing_and_current_focus():
    """组合键提交后平移继续核验当前绑定窗口，按键保持逆序释放。"""
    from game_automation.platform.macos.adapters.window_input import (
        MacOSWindowInputDevice,
    )
    from tests.test_window_input import Quartz

    session, binding, _, clock, _ = setup()
    session.backend = "macos-window"
    q = Quartz()
    q.kCGWindowBounds = "bounds"
    binding.quartz = q
    post = q.CGEventPost

    def post_and_move(tap, event):
        """首个修饰键提交后移动同一窗口。"""
        post(tap, event)
        if len(q.events) == 1:
            binding.bounds.update(X=500, Y=600)

    q.CGEventPost = post_and_move
    device = MacOSWindowInputDevice(
        session,
        quartz=q,
        activation=lambda *args: 42,
        frontmost_pid=lambda: 42,
        keyboard_focus=lambda pid: SimpleNamespace(
            title="页面", rect=session.current_rect()
        ),
        clock=clock,
        sleep=clock.sleep,
    )
    session.execute_input(lambda: device.hotkey(("ctrl", "a")))
    assert [event["kind"] for _, event in q.events] == [
        (59, True),
        (0, True),
        (0, False),
        (59, False),
    ]
    assert session.rect == Rect(500, 600, 80, 60)


def test_foreground_wait_excludes_translation_recovery_pause():
    """前台普通等待也使用扣除平移恢复暂停的有效任务时间。"""
    from game_automation.platform.macos.adapters.window_input import (
        MacOSWindowInputDevice,
    )

    session, binding, _, clock, _ = setup()
    session.backend = "macos-window"
    binding.bounds.update(X=501)
    device = MacOSWindowInputDevice(session, clock=clock, sleep=clock.sleep)
    device.wait(0.1)
    assert clock() == pytest.approx(10.14)
    assert session.task_time() == pytest.approx(10.1)
    assert session.rect.left == 501
