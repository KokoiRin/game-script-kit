"""验证窗口采集的身份隔离、一帧批量匹配和资源清理。

本 module 用系统窗口表与截图命令替身，不调用真实截图、权限或焦点控制。
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from game_automation.platform.macos.adapters.window_state_probe import (
    MacOSWindowStateProbe,
    WindowFrameSource,
)
from game_automation.portable.application.window_state_rules import WindowStateRules
from game_automation.portable.domain import ImageTemplate, Rect, ScreenStateCandidate
from game_automation.portable.preparation.models import DesktopWindow


def quartz(windows):
    """提供可注入的系统窗口表。"""
    return SimpleNamespace(
        kCGWindowListOptionAll=0,
        kCGWindowListOptionOnScreenOnly=1,
        kCGWindowListExcludeDesktopElements=2,
        kCGNullWindowID=0,
        kCGWindowOwnerPID="pid",
        kCGWindowLayer="layer",
        kCGWindowName="title",
        kCGWindowBounds="bounds",
        kCGWindowNumber="id",
        CGWindowListCopyWindowInfo=lambda *args: windows,
    )


def test_window_capture_is_scoped_to_pid_title_and_window_id(tmp_path):
    """窗口截图只使用明确窗口编号，不激活应用或截取整个桌面。"""
    windows = [
        {
            "pid": 42,
            "layer": 0,
            "title": "页面",
            "bounds": {"X": 20, "Y": 30, "Width": 80, "Height": 60},
            "id": 100,
        },
        {
            "pid": 43,
            "layer": 0,
            "title": "页面",
            "bounds": {"X": 0, "Y": 0, "Width": 80, "Height": 60},
            "id": 101,
        },
    ]
    calls = []

    def capture(command, **kwargs):
        """模拟按窗口截图并验证系统调用有超时。"""
        calls.append(command)
        assert kwargs["timeout"] == 2
        Image.new("RGB", (160, 120)).save(command[-1])

    source = WindowFrameSource(
        DesktopWindow("42:1:hash", "App", "页面", Rect(20, 30, 80, 60)),
        quartz=quartz(windows),
        command_runner=capture,
    )
    try:
        assert source.screenshot().size == (160, 120)
        assert source.size() == (80, 60)
        assert calls[0][:5] == ["/usr/sbin/screencapture", "-x", "-o", "-l", "100"]
        image_path = Path(calls[0][-1])
    finally:
        source.close()
    assert not image_path.exists()


def test_closed_window_never_returns_an_old_image():
    """目标消失时必须报错，不能采集同名其他应用或返回旧画面。"""
    with pytest.raises(RuntimeError, match="已关闭"):
        WindowFrameSource(
            DesktopWindow("42:1", "App", "页面", Rect(0, 0, 80, 60)), quartz=quartz([])
        )


def test_batch_probe_uses_one_frame_for_all_templates_and_relative_regions(tmp_path):
    """多素材使用同一窗口画面，结果坐标不包含窗口的屏幕偏移。"""
    import numpy as np

    from game_automation.portable.domain import ImageSearchSpec

    image = Image.fromarray(
        np.random.default_rng(42).integers(0, 255, (120, 160, 3), dtype=np.uint8)
    )
    path = tmp_path / "target.png"
    image.crop((20, 40, 40, 60)).save(path)

    class Source:
        def __init__(self):
            """初始化截图次数。"""
            self.calls = 0

        def screenshot(self):
            """返回同一帧而不读取真实设备。"""
            self.calls += 1
            return image

        def size(self):
            """返回二倍像素截图对应的逻辑窗口大小。"""
            return (80, 60)

        def close(self):
            """无需回收外部设备。"""

    source = Source()
    candidates = tuple(
        ScreenStateCandidate(
            name, ImageSearchSpec(ImageTemplate(str(path)), region=Rect(0, 0, 40, 40))
        )
        for name in ("A", "B")
    )
    probe = MacOSWindowStateProbe(
        DesktopWindow("42:1", "App", "页面", Rect(100, 200, 80, 60)),
        WindowStateRules(candidates, 80, 60, 160, 120),
        source=source,
    )
    result = probe.read()
    assert source.calls == 1
    assert result.timing is not None
    assert result.timing.screenshot_ms >= 0
    assert result.timing.recognition_ms >= 0
    assert result.timing.screenshot_ms + result.timing.recognition_ms == pytest.approx(
        result.elapsed_ms
    )
    assert all(item.found for item in result.candidates)
    assert result.candidates[0].match.rect == Rect(10, 20, 10, 10)


def test_same_title_replacement_is_not_adopted():
    """首帧固定编号后拒绝同进程同名替代窗口。"""
    windows = [
        {
            "pid": 42,
            "layer": 0,
            "title": "页面",
            "bounds": {"X": 0, "Y": 0, "Width": 80, "Height": 60},
            "id": 100,
        }
    ]

    def capture(command, **kwargs):
        """写入受控假截图。"""
        Image.new("RGB", (160, 120)).save(command[-1])

    source = WindowFrameSource(
        DesktopWindow("42:1", "App", "页面", Rect(0, 0, 80, 60)),
        quartz=quartz(windows),
        command_runner=capture,
    )
    try:
        source.screenshot()
        windows[0]["id"] = 101
        with pytest.raises(RuntimeError, match="已关闭"):
            source.screenshot()
    finally:
        source.close()


def test_geometry_failure_survives_matching_boundary(tmp_path):
    """像素比例变化的中文原因穿过匹配器，不能泛化成依赖错误。"""
    path = tmp_path / "target.png"
    Image.new("RGB", (5, 5)).save(path)

    class Source:
        def screenshot(self):
            """模拟显示缩放变化后的画面。"""
            return Image.new("RGB", (80, 60))

        def size(self):
            """提供原逻辑尺寸。"""
            return (80, 60)

        def close(self):
            """无需回收内存画面。"""

    probe = MacOSWindowStateProbe(
        DesktopWindow("42:1", "App", "页面", Rect(0, 0, 80, 60)),
        WindowStateRules(
            (ScreenStateCandidate("A", ImageTemplate(str(path))),), 80, 60, 160, 120
        ),
        source=Source(),
    )
    with pytest.raises(RuntimeError, match="像素尺寸已变化"):
        probe.read()


def test_initial_binding_uses_unique_geometry_instead_of_ax_title():
    """AX 私有浏览标题与 CG 标题不同仍按唯一完整几何绑定，移动不失效。"""
    windows = [
        {
            "pid": 42,
            "layer": 0,
            "title": "页面",
            "bounds": {"X": 20, "Y": 30, "Width": 80, "Height": 60},
            "id": 100,
        },
        {
            "pid": 42,
            "layer": 0,
            "title": "页面，无痕浏览",
            "bounds": {"X": 200, "Y": 300, "Width": 80, "Height": 60},
            "id": 101,
        },
    ]
    captured = []

    def capture(command, **kwargs):
        """记录被选窗口并写入假画面。"""
        captured.append(command[4])
        Image.new("RGB", (160, 120)).save(command[-1])

    source = WindowFrameSource(
        DesktopWindow("42:1", "App", "页面，无痕浏览", Rect(20, 30, 80, 60)),
        quartz=quartz(windows),
        command_runner=capture,
    )
    try:
        source.screenshot()
        windows[0]["bounds"].update(X=50, Y=60)
        source.screenshot()
        assert captured == ["100", "100"]
    finally:
        source.close()


def test_duplicate_geometry_is_ambiguous_even_with_matching_ax_title():
    """两个同进程窗口几何相同时不能用标题猜测对应关系。"""
    windows = [
        {
            "pid": 42,
            "layer": 0,
            "title": title,
            "bounds": {"X": 20, "Y": 30, "Width": 80, "Height": 60},
            "id": number,
        }
        for title, number in [("页面", 100), ("另一个标题", 101)]
    ]
    with pytest.raises(RuntimeError, match="唯一|多个"):
        WindowFrameSource(
            DesktopWindow("42:1", "App", "页面", Rect(20, 30, 80, 60)),
            quartz=quartz(windows),
        )


def test_bound_cg_title_change_invalidates_capture():
    """编号不变但 CG 标题变化时也失效，避免继续匹配其他页面。"""
    windows = [
        {
            "pid": 42,
            "layer": 0,
            "title": "页面",
            "bounds": {"X": 0, "Y": 0, "Width": 80, "Height": 60},
            "id": 100,
        }
    ]
    source = WindowFrameSource(
        DesktopWindow("42:1", "App", "页面", Rect(0, 0, 80, 60)), quartz=quartz(windows)
    )
    try:
        windows[0]["title"] = "其他页面"
        with pytest.raises(RuntimeError, match="标题|已关闭"):
            source.screenshot()
    finally:
        source.close()


def test_window_number_accepts_bridged_integer_subclass():
    """PyObjC 桥接整数编号可直接绑定，不要求精确内置类型。"""

    class BridgedNumber(int):
        """模拟系统桥接整数。"""

    windows = [
        {
            "pid": 42,
            "layer": 0,
            "title": "页面",
            "bounds": {"X": 0, "Y": 0, "Width": 80, "Height": 60},
            "id": BridgedNumber(100),
        }
    ]

    def capture(command, **kwargs):
        """验证桥接编号原值传入截图边界。"""
        assert command[4] == "100"
        Image.new("RGB", (160, 120)).save(command[-1])

    source = WindowFrameSource(
        DesktopWindow("42:1", "App", "页面", Rect(0, 0, 80, 60)),
        quartz=quartz(windows),
        command_runner=capture,
    )
    try:
        assert source.screenshot().size == (160, 120)
    finally:
        source.close()


@pytest.mark.parametrize("number", [True, False, 0, -1, 100.0, "100"])
def test_invalid_window_number_is_not_coerced(number):
    """布尔、非正数和非整数编号都拒绝，不能截断浮点编号。"""
    windows = [
        {
            "pid": 42,
            "layer": 0,
            "title": "页面",
            "bounds": {"X": 0, "Y": 0, "Width": 80, "Height": 60},
            "id": number,
        }
    ]
    with pytest.raises(RuntimeError, match="有效编号"):
        WindowFrameSource(
            DesktopWindow("42:1", "App", "页面", Rect(0, 0, 80, 60)),
            quartz=quartz(windows),
        )


@pytest.mark.parametrize("changed", [{"Width": 81}, {"Height": 59}])
def test_window_size_error_reports_original_and_current_geometry(changed):
    """尺寸变化错误保留前后矩形，便于定位短时系统窗口变化。"""
    from game_automation.platform.macos.adapters.window_identity import BoundWindow

    windows = [
        {
            "pid": 42,
            "layer": 0,
            "title": "页面",
            "bounds": {"X": 20, "Y": 30, "Width": 80, "Height": 60},
            "id": 100,
        }
    ]
    binding = BoundWindow(
        DesktopWindow("42:1", "App", "页面", Rect(20, 30, 80, 60)),
        quartz=quartz(windows),
    )
    windows[0]["bounds"].update(changed)
    bounds = windows[0]["bounds"]
    with pytest.raises(RuntimeError) as caught:
        binding.check()
    message = str(caught.value)
    assert "尺寸已变化" in message
    assert "原窗口=(20, 30, 80, 60)" in message
    assert (
        f"当前窗口={(bounds['X'], bounds['Y'], bounds['Width'], bounds['Height'])}"
        in message
    )


def test_existing_offscreen_identity_is_temporary_but_replacement_is_terminal():
    """用全部窗口核实固定身份，区分隐藏和真正被替换。"""
    from game_automation.platform.macos.adapters.window_identity import (
        BoundWindow,
        WindowPresentationUnavailable,
    )
    from game_automation.portable.application.capture_errors import WindowCaptureError

    windows = [
        {
            "pid": 42,
            "layer": 0,
            "title": "页面",
            "bounds": {"X": 0, "Y": 0, "Width": 80, "Height": 60},
            "id": 100,
        }
    ]
    q = quartz(windows)
    visible = [True]

    def rows(options, window_id):
        """不可见时仅全部窗口查询仍能找到原编号。"""
        return (
            windows
            if visible[0] or not options & q.kCGWindowListOptionOnScreenOnly
            else []
        )

    q.CGWindowListCopyWindowInfo = rows
    binding = BoundWindow(
        DesktopWindow("42:1", "App", "页面", Rect(0, 0, 80, 60)), quartz=q
    )
    visible[0] = False
    with pytest.raises(WindowPresentationUnavailable):
        binding.check()
    windows[0]["id"] = 101
    with pytest.raises(WindowCaptureError) as caught:
        binding.check()
    assert not isinstance(caught.value, WindowPresentationUnavailable)
