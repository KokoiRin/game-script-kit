"""验证原生会话的源所有权、坐标和输入证明，不访问系统窗口。"""

from types import SimpleNamespace

import pytest
from PIL import Image

from game_automation.platform.macos.adapters.window_runtime import (
    MacOSRuntimeFactory,
    MacOSWindowSession,
    NativeRuntimeLease,
)
from game_automation.platform.macos.adapters.window_vision import (
    WindowColorReader,
    WindowImageLocator,
    WindowStateReader,
)
from game_automation.portable.application.capture_errors import WindowCaptureError
from game_automation.portable.application.runtime_ports import RuntimePorts
from game_automation.portable.application.window_state_rules import WindowStateRules
from game_automation.portable.domain import (
    AreaWindow,
    Color,
    ImageBatchMatchResult,
    ImageMatch,
    ImageSearchRequest,
    ImageTemplate,
    Point,
    Rect,
)
from game_automation.portable.domain.screen_state import FrameProof
from game_automation.portable.domain.task import ScriptTarget
from game_automation.portable.engine.cancellation import ScriptCancelledError
from game_automation.portable.engine.script_requirements import ScriptRequirements
from game_automation.portable.preparation.models import DesktopWindow


class Clock:
    def __init__(self):
        """建立确定性单调时钟。"""
        self.now = 10.0

    def __call__(self):
        """返回当前时间。"""
        return self.now

    def sleep(self, amount):
        """跳到下一次检查。"""
        self.now += amount


class Binding:
    def __init__(self, window):
        """保存固定窗口的可变系统信息。"""
        self.number = 7
        self.window = window
        self.quartz = SimpleNamespace(kCGWindowBounds="bounds")
        self.bounds = {
            "X": window.rect.left,
            "Y": window.rect.top,
            "Width": window.rect.width,
            "Height": window.rect.height,
        }
        self.error = None

    def check(self):
        """模拟身份检查。"""
        if self.error:
            raise WindowCaptureError(self.error)
        return {"bounds": self.bounds}


class Source:
    def __init__(self, proofs, *, fail_close=False):
        """提供可重复读取的源证明序列。"""
        self.proofs = list(proofs)
        self.proof = None
        self.closed = 0
        self.fail_close = fail_close
        self.captures = 0

    def screenshot(self):
        """捕获图像副本，不制造系统新证明。"""
        self.captures += 1
        if self.proofs:
            self.proof = self.proofs.pop(0)
        image = Image.new("RGB", (160, 90), (1, 2, 3))
        image.putpixel((10, 9), (71, 72, 73))
        return image

    def close(self):
        """记录唯一关闭尝试。"""
        self.closed += 1
        if self.fail_close:
            raise RuntimeError("stop barrier failed")


_DEFAULT_PROOFS = (FrameProof(1, 10),)


def setup_session(proofs=_DEFAULT_PROOFS, **kwargs):
    """建立非零原点、独立两轴像素比例的会话。"""
    window = DesktopWindow("42:1", "Example", "Game", Rect(100, 200, 80, 60))
    rules = WindowStateRules((), 80, 60, 160, 90)
    clock = Clock()
    binding = Binding(window)
    session = MacOSWindowSession(
        window, binding, rules, clock=clock, sleep=clock.sleep, **kwargs
    )
    source = Source(proofs)
    session.attach_source(source)
    return session, source, binding, clock


def test_color_uses_independent_pixel_ratios_and_global_origin():
    """逻辑点5,6应映射为原始像素10,9。"""
    session, source, _, _ = setup_session()
    assert WindowColorReader(session).read_color(Point(105, 206)) == Color(71, 72, 73)
    assert source.captures == 1
    with pytest.raises(ValueError, match="超出"):
        WindowColorReader(session).read_color(Point(99, 206))


def test_session_rejects_move_and_replacement_before_capture():
    """位置变化和身份替换都不能继续读取旧窗口。"""
    session, source, binding, _ = setup_session()
    binding.bounds["X"] = 101
    with pytest.raises(WindowCaptureError, match="位置"):
        session.screenshot()
    assert source.captures == 0
    binding.bounds["X"] = 100
    binding.error = "window replaced"
    with pytest.raises(WindowCaptureError, match="replaced"):
        session.screenshot()


def test_input_requires_newer_sequence_and_later_system_timestamp():
    """旧缓存及输入前时间戳不能确认输入效果。"""
    proofs = (
        FrameProof(1, 9.9),
        FrameProof(1, 9.9),
        FrameProof(2, 9.99),
        FrameProof(3, 10.03),
    )
    session, source, _, clock = setup_session(proofs)
    session.screenshot().close()
    session.input_finished()
    session.screenshot().close()
    assert source.captures == 4
    assert session.proof.sequence == 3
    assert clock.now >= 10.03


def test_stale_repeated_proof_times_out_without_renewing_age():
    """多次读取不会刷新源时间。"""
    session, source, _, clock = setup_session((FrameProof(1, 7),), capture_timeout=0.05)
    with pytest.raises(WindowCaptureError, match="过期"):
        session.screenshot()
    assert clock.now >= 10.05
    assert source.proof.captured_at == 7


def test_cancelled_wait_still_allows_owned_source_cleanup():
    """取消在捕获前生效，关闭不再次受取消拦截。"""
    token = SimpleNamespace(is_cancelled=lambda: True)
    session, source, _, _ = setup_session(cancellation=token)
    with pytest.raises(ScriptCancelledError):
        session.screenshot()
    session.close()
    session.close()
    assert source.closed == 1


def test_image_adapter_translates_roi_match_and_best_rect_once():
    """命中与未命中的最佳位置都维持引擎全局坐标契约。"""
    session, _, _, _ = setup_session()
    template = ImageTemplate("unused.png")
    local_match = ImageMatch(Rect(5, 6, 10, 8), 0.95)
    seen = []

    class Locator:
        def __init__(self, *, backend):
            """验证显式窗口源注入。"""
            assert backend is session

        def locate(self, template, **kwargs):
            """记录局部区域。"""
            seen.append(kwargs["region"])
            return local_match

        def locate_requests(self, requests, **kwargs):
            """模拟命中、未命中与跳过。"""
            seen.extend(r.region for r in requests)
            return (
                ImageBatchMatchResult(template, local_match, 1),
                ImageBatchMatchResult(
                    template, None, 1, best_confidence=0.6, best_rect=Rect(8, 9, 10, 8)
                ),
                ImageBatchMatchResult.skipped_result(template),
            )

    locator = WindowImageLocator(session, locator_factory=Locator)
    roi = Rect(101, 202, 30, 20)
    assert locator.locate(template, region=roi).rect == Rect(105, 206, 10, 8)
    results = locator.locate_requests(
        tuple(ImageSearchRequest(template, roi) for _ in range(3))
    )
    assert results[0].match.rect == Rect(105, 206, 10, 8)
    assert results[0].best_rect == Rect(105, 206, 10, 8)
    assert results[1].best_rect == Rect(108, 209, 10, 8)
    assert results[2].best_rect is None
    assert seen == [Rect(1, 2, 30, 20)] * 4
    with pytest.raises(ValueError, match="超出"):
        locator.locate(template, region=Rect(99, 200, 5, 5))


def test_factory_retains_lease_when_capture_shutdown_fails(monkeypatch, tmp_path):
    """停流屏障失败后不允许新会话并明确提示重启后台。"""
    from game_automation.platform.macos.adapters import window_runtime as module

    rules = WindowStateRules((), 80, 60, 160, 90)
    monkeypatch.setattr(module, "load_window_state_rules", lambda workspace: rules)
    candidate = SimpleNamespace(
        pid=42, window_number=1, title="Game", rect=Rect(100, 200, 80, 60)
    )
    source = Source((FrameProof(1, 10),), fail_close=True)

    class Session:
        def __init__(self, window, binding, rules, **kwargs):
            """提供不访问系统的会话。"""
            self.window = window

        def attach_source(self, value):
            """保存唯一源。"""
            self.source = value

        def ports(self, requirements):
            """返回虚假设备端口。"""
            return RuntimePorts(AreaWindow(self.window.rect), object())

        def close(self):
            """交由实际源执行关闭。"""
            self.source.close()

    factory = MacOSRuntimeFactory(
        tmp_path,
        lease=NativeRuntimeLease(),
        backend_factory=lambda: SimpleNamespace(list_windows=lambda app: (candidate,)),
        binding_factory=Binding,
        source_factory=lambda *args, **kwargs: source,
        session_factory=Session,
    )
    target = ScriptTarget("Example", "Game", 80, 60, backend="macos-window")
    with pytest.raises(RuntimeError, match="stop barrier"):
        with factory.open(target, ScriptRequirements(), None, None):
            pass
    with pytest.raises(RuntimeError, match="重新启动后台"):
        with factory.open(target, ScriptRequirements(), None, None):
            pass
    assert source.closed == 1


def test_native_state_reader_uses_shared_source_and_priority_points():
    """状态端口复用既有多点循环且一次只取一帧。"""
    from game_automation.portable.domain import ScreenStateCandidate
    from game_automation.portable.domain.color_pattern import ColorPattern, ColorPoint

    session, source, _, _ = setup_session()
    pattern = ColorPattern(
        (ColorPoint(10, 9, (71, 72, 73), 0), ColorPoint(12, 12, (1, 2, 3), 0)), 0
    )
    session.rules = WindowStateRules(
        (
            ScreenStateCandidate("对话", ImageTemplate("no-file-dialog.png")),
            ScreenStateCandidate("主页", ImageTemplate("no-file-home.png")),
        ),
        80,
        60,
        160,
        90,
        (20, 10),
        (pattern, pattern),
    )
    reader = WindowStateReader(session)
    assert reader.read_current_state() == "对话"
    assert source.captures == 1
    assert source.closed == 0
    session.close()
    assert source.closed == 1


def test_capture_cancellation_crosses_template_and_state_boundary_unchanged():
    """匹配器不能把协作取消包装成普通识图失败。"""
    session, source, _, _ = setup_session(
        cancellation=SimpleNamespace(is_cancelled=lambda: True)
    )
    template = ImageTemplate("unused.png")
    with pytest.raises(ScriptCancelledError):
        WindowImageLocator(session).locate(template)
    with pytest.raises(ScriptCancelledError):
        WindowStateReader(session).read_current_state()
    assert source.captures == 0


def test_real_matcher_preserves_retina_and_window_origin(tmp_path):
    """真实内存模板在局部 ROI 搜索后只加一次窗口原点。"""
    import random

    session, source, _, _ = setup_session()
    randomizer = random.Random(5)
    image = Image.new("RGB", (160, 90))
    image.putdata(
        [tuple(randomizer.randrange(256) for _ in range(3)) for _ in range(160 * 90)]
    )
    template_path = tmp_path / "template.png"
    image.crop((20, 15, 40, 30)).save(template_path)

    def screenshot():
        """返回确定性窗口内存图并保留真实源证明。"""
        source.captures += 1
        source.proof = FrameProof(1, 10)
        return image.copy()

    source.screenshot = screenshot
    result = WindowImageLocator(session).locate(
        ImageTemplate(str(template_path)),
        region=Rect(105, 205, 30, 20),
        min_confidence=0.99,
    )
    assert result.rect == Rect(110, 210, 10, 10)
    assert source.captures == 1


def test_state_reader_uses_call_threshold_unless_rule_has_explicit_threshold(tmp_path):
    """调用阈值只补足未配置阈值的模板，多点规则语义保持独立。"""
    import random

    from game_automation.portable.domain import ImageSearchSpec, ScreenStateCandidate

    session, source, _, _ = setup_session()
    randomizer = random.Random(11)
    image = Image.new("RGB", (160, 90))
    image.putdata(
        [tuple(randomizer.randrange(256) for _ in range(3)) for _ in range(160 * 90)]
    )
    template = image.crop((20, 15, 40, 30))
    for x in range(3):
        for y in range(3):
            template.putpixel((x, y), (255, 255, 255))
    path = tmp_path / "threshold.png"
    template.save(path)

    def screenshot():
        """提供相似但非完全一致的当前帧。"""
        source.proof = FrameProof(1, 10)
        return image.copy()

    source.screenshot = screenshot
    candidate = ScreenStateCandidate("page", ImageTemplate(str(path)))
    session.rules = WindowStateRules((candidate,), 80, 60, 160, 90)
    reader = WindowStateReader(session)
    assert reader.read_current_state(min_confidence=0.999) == "未知"
    assert reader.read_current_state(min_confidence=0.8) == "page"
    explicit = ScreenStateCandidate(
        "page", ImageSearchSpec(ImageTemplate(str(path)), min_confidence=0.8)
    )
    session.rules = WindowStateRules((explicit,), 80, 60, 160, 90)
    assert WindowStateReader(session).read_current_state(min_confidence=0.999) == "page"


def test_factory_uses_new_owned_source_for_each_successful_or_cancelled_run(
    monkeypatch, tmp_path
):
    """成功及取消都释放租约，下一轮获得独立源而不借用旧缓存。"""
    from game_automation.platform.macos.adapters import window_runtime as module

    rules = WindowStateRules((), 80, 60, 160, 90)
    monkeypatch.setattr(module, "load_window_state_rules", lambda workspace: rules)
    candidate = SimpleNamespace(
        pid=42, window_number=1, title="Game", rect=Rect(100, 200, 80, 60)
    )
    sources = []

    def source_factory(window, pixel_size, *, hz, binding):
        """记录每次独立分配与配置像素尺寸。"""
        assert pixel_size == (160, 90)
        assert hz == 5
        source = Source((FrameProof(1, 10),))
        sources.append(source)
        return source

    factory = MacOSRuntimeFactory(
        tmp_path,
        lease=NativeRuntimeLease(),
        backend_factory=lambda: SimpleNamespace(list_windows=lambda app: (candidate,)),
        binding_factory=Binding,
        source_factory=source_factory,
    )
    target = ScriptTarget("Example", "Game", 80, 60, backend="macos-window")
    with factory.open(target, ScriptRequirements(), None, None) as first:
        assert first.window == AreaWindow(candidate.rect)
    with pytest.raises(ScriptCancelledError):
        with factory.open(target, ScriptRequirements(), None, None):
            raise ScriptCancelledError("cancel")
    with factory.open(target, ScriptRequirements(), None, None):
        pass
    assert len(sources) == 3
    assert all(source.closed == 1 for source in sources)


def test_process_lease_blocks_second_factory_and_workspace_after_failed_close(
    monkeypatch, tmp_path
):
    """失败租约属于进程，换工厂或工作区都不能绕过，源仍被强引用。"""
    import gc
    import weakref

    from game_automation.platform.macos.adapters import window_runtime as module

    # 使用隔离进程租约，避免故障注入污染其他测试。
    monkeypatch.setattr(module, "_PROCESS_LEASE", module.NativeRuntimeLease())
    rules = WindowStateRules((), 80, 60, 160, 90)
    monkeypatch.setattr(module, "load_window_state_rules", lambda workspace: rules)
    candidate = SimpleNamespace(
        pid=42, window_number=1, title="Game", rect=Rect(100, 200, 80, 60)
    )
    refs = []

    def source_factory(*args, **kwargs):
        """分配会关闭失败的源，并只在测试中保存弱引用。"""
        source = Source((FrameProof(1, 10),), fail_close=True)
        refs.append(weakref.ref(source))
        return source

    kwargs = {
        "backend_factory": lambda: SimpleNamespace(
            list_windows=lambda app: (candidate,)
        ),
        "binding_factory": Binding,
        "source_factory": source_factory,
    }
    first = MacOSRuntimeFactory(tmp_path / "workspace-a", **kwargs)
    second = MacOSRuntimeFactory(tmp_path / "workspace-b", **kwargs)
    target = ScriptTarget("Example", "Game", 80, 60, backend="macos-window")
    with pytest.raises(RuntimeError, match="stop barrier"):
        with first.open(target, ScriptRequirements(), None, None):
            pass
    del first
    gc.collect()
    assert refs[0]() is not None
    with pytest.raises(RuntimeError, match="重新启动后台"):
        with second.open(target, ScriptRequirements(), None, None):
            pass
    assert len(refs) == 1


def test_session_selects_isolated_background_device_with_same_visual_source(
    monkeypatch,
):
    """后端只改变输入adapter，窗口及视觉仍来自原会话。"""
    from game_automation.platform.macos.adapters import (
        window_background_input as module,
    )

    session, source, _, _ = setup_session()
    session.backend = "macos-window-background"

    class Device:
        def __init__(self, owner):
            """只保存会话引用，不访问系统私有符号。"""
            assert owner is session

    monkeypatch.setattr(module, "MacOSBackgroundWindowInputDevice", Device)
    ports = session.ports(
        ScriptRequirements(
            needs_color_reader=True,
            needs_image_locator=True,
            needs_screen_state_reader=True,
        )
    )
    assert isinstance(ports.device, Device)
    assert ports.color_reader.session is session
    assert ports.image_locator.session is session
    assert ports.screen_state_reader._backend == "macos-window-background"
    assert source.captures == 0


@pytest.mark.parametrize(
    "bounds",
    [
        {"X": 101, "Y": 200, "Width": 80, "Height": 60},
        {"X": 100, "Y": 190, "Width": 80, "Height": 60},
    ],
)
def test_window_move_error_reports_original_and_current_geometry(bounds):
    """移动错误必须提供前后逻辑矩形，以区分系统调整和素材问题。"""
    session, source, binding, _ = setup_session()
    binding.bounds = bounds
    with pytest.raises(WindowCaptureError) as caught:
        session.screenshot()
    message = str(caught.value)
    assert "位置已变化" in message
    assert "原窗口=(100, 200, 80, 60)" in message
    assert (
        f"当前窗口={(bounds['X'], bounds['Y'], bounds['Width'], bounds['Height'])}"
        in message
    )
    assert "重新运行" in message
    assert source.captures == 0
