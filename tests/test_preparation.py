"""验证素材准备会话的公共行为，不运行脚本、不访问真实桌面。

本 module 通过窗口、截图、裁图与存储端口替身验证坐标和冻结帧契约。
"""

import pytest
import subprocess
import sys
from pathlib import Path

from game_automation.portable.domain.geometry import Point, Rect
from game_automation.portable.preparation.models import DesktopWindow, ImageData
from game_automation.portable.preparation.service import PreparationService


class PreparationBackend:
    """记录素材准备的外部调用，并提供两倍像素比例的截图。"""

    def __init__(self):
        """初始化候选窗口、调用记录和保存记录。"""
        self.window = DesktopWindow("42:1", "Game", "任务窗口", Rect(100, 200, 80, 60))
        self.calls = []
        self.saved = []

    def list_windows(self, application):
        """查询窗口不激活目标或执行输入。"""
        self.calls.append(("list", application))
        return (self.window,)

    def focus_window(self, application, window_id):
        """按明确标识定位窗口，返回捕获时的最新范围。"""
        self.calls.append(("focus", application, window_id))
        return self.window

    def capture(self, region):
        """按窗口范围返回截图值对象。"""
        self.calls.append(("capture", region))
        return ImageData(b"frame", 160, 120)

    def crop(self, image, region):
        """记录裁图来源，不能重新读取桌面。"""
        self.calls.append(("crop", image.png, region))
        return ImageData(b"crop", region.width, region.height)

    def save_png(self, name, png):
        """记录模板保存并返回相对 assets 的路径。"""
        self.saved.append((name, png))
        return f"{name}.png"


@pytest.fixture
def preparation():
    """创建不依赖脚本 catalog 或 runner 的素材准备会话。"""
    backend = PreparationBackend()
    return PreparationService(windows=backend, capture=backend, images=backend, templates=backend), backend


def test_preparation_lists_windows_without_capturing(preparation):
    """窗口列表查询不会触发截图或运行。"""
    service, backend = preparation
    assert service.list_windows("Game") == (backend.window,)
    assert backend.calls == [("list", "Game")]


def test_capture_and_crop_use_the_same_frozen_frame(preparation):
    """裁图必须使用指定的截图帧，保持像素内容和位置一致。"""
    service, backend = preparation
    frame = service.capture_window("Game", "42:1")
    crop = service.save_crop(frame.id, Rect(20, 40, 30, 20), "任务入口")

    assert frame.window == backend.window
    assert frame.captured_at > 0
    assert crop == "任务入口.png"
    assert backend.calls == [
        ("focus", "Game", "42:1"), ("capture", Rect(100, 200, 80, 60)),
        ("crop", b"frame", Rect(20, 40, 30, 20)),
    ]
    assert backend.saved == [("任务入口", b"crop")]


def test_point_converts_image_pixels_to_window_and_screen_coordinates(preparation):
    """两倍像素截图取点得到窗口相对坐标及屏幕坐标。"""
    service, _ = preparation
    frame = service.capture_window("Game", "42:1")
    assert service.locate_point(frame.id, Point(40, 60)) == (Point(20, 30), Point(120, 230))


@pytest.mark.parametrize("region", [Rect(-1, 0, 10, 10), Rect(150, 0, 20, 10), Rect(0, 115, 10, 10)])
def test_crop_rejects_out_of_bounds_without_writing(preparation, region):
    """越界框选不能以补黑边的方式生成误导性模板。"""
    service, backend = preparation
    frame = service.capture_window("Game", "42:1")
    with pytest.raises(ValueError, match="outside"):
        service.save_crop(frame.id, region, "bad")
    assert backend.saved == []


def test_new_capture_invalidates_old_frame(preparation):
    """重新截图后拒绝旧帧操作，避免把旧框选应用到新画面。"""
    service, _ = preparation
    old = service.capture_window("Game", "42:1")
    new = service.capture_window("Game", "42:1")
    assert old.id != new.id
    with pytest.raises(LookupError, match="capture again"):
        service.save_crop(old.id, Rect(0, 0, 10, 10), "old")


def test_failed_capture_does_not_leave_a_previous_frame_usable(preparation):
    """捕获新目标失败时不得继续在旧目标上取点或保存模板。"""
    service, backend = preparation
    old = service.capture_window("Game", "42:1")

    def fail(region):
        """模拟截图权限失败。"""
        raise RuntimeError("capture unavailable")

    backend.capture = fail
    with pytest.raises(RuntimeError, match="unavailable"):
        service.capture_window("Game", "42:1")
    with pytest.raises(LookupError):
        service.locate_point(old.id, Point(1, 1))


def test_preparation_shell_does_not_import_execution_services():
    """独立准备壳装配不能通过包初始化隐式加载 runner、控制台或脚本目录。"""
    code = """
import sys
from pathlib import Path
from game_automation.platform.local_desktop.entrypoints.desktop_backend import DesktopBackend
from game_automation.platform.local_desktop.preparation_composition import build_preparation_service
build_preparation_service(Path('/tmp'))
for suffix in ('engine.runner', 'application.script_run', 'application.local_control', 'scripts_manager.catalog'):
    name = 'game_automation.portable.' + suffix
    assert name not in sys.modules, name
assert 'pyautogui' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
