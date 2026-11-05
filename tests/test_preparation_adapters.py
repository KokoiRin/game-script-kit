"""验证准备 adapter 的图像与文件契约，真实桌面由 backend 替身隔离。

本 module 检查像素比例、冻结裁图及模板落盘，不执行脚本。
"""

import io

from PIL import Image
import pytest

from game_automation.platform.desktop.adapters.preparation import DesktopFrameCapture, PillowImageEditor, WorkspaceTemplateStore
from game_automation.portable.domain.geometry import Rect


def test_preparation_capture_reuses_desktop_pixel_scaling():
    """窗口逻辑坐标与二倍像素截图之间应正确转换。"""
    class Backend:
        def screenshot(self):
            """返回二倍像素桌面。"""
            return Image.new("RGB", (160, 120), "red")

        def size(self):
            """返回鼠标坐标系尺寸。"""
            return (80, 60)

    capture = DesktopFrameCapture(backend=Backend())
    frame = capture.capture(Rect(10, 20, 30, 20))
    assert (frame.width, frame.height) == (60, 40)
    crop = PillowImageEditor().crop(frame, Rect(2, 4, 10, 8))
    with Image.open(io.BytesIO(crop.png)) as decoded:
        assert decoded.size == (10, 8)
        assert decoded.getpixel((0, 0)) == (255, 0, 0)
    with pytest.raises(RuntimeError, match="outside"):
        capture.capture(Rect(70, 0, 20, 20))


def test_preparation_store_saves_under_assets_without_overwriting(tmp_path):
    """模板路径可用于现有脚本资源，重名不能覆盖用户素材。"""
    store = WorkspaceTemplateStore(tmp_path)
    assert store.save_png("任务入口", b"original") == "任务入口.png"
    assert (tmp_path / "assets" / "任务入口.png").read_bytes() == b"original"
    with pytest.raises(FileExistsError):
        store.save_png("任务入口", b"replacement")
    assert (tmp_path / "assets" / "任务入口.png").read_bytes() == b"original"


@pytest.mark.parametrize("name", ["", "../outside", "/tmp/outside", "a/b", "a\\b", ".", ".."])
def test_preparation_store_rejects_non_template_names(tmp_path, name):
    """用户输入只作为模板名称，不能变成工作区外的文件路径。"""
    with pytest.raises(ValueError, match="template name"):
        WorkspaceTemplateStore(tmp_path).save_png(name, b"data")
    assert list(tmp_path.iterdir()) == []
