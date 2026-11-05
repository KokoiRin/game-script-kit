"""验证准备界面的窗口候选与激活适配，不访问 macOS framework。

本 module 测试候选标识、窗口消失或歧义以及移动后的范围，不解释脚本。
"""

from dataclasses import replace

import pytest

from game_automation.platform.macos.adapters.application_window import MacOSWindowCandidate
from game_automation.platform.macos.adapters.preparation_windows import MacOSPreparationWindows
from game_automation.portable.domain.geometry import Rect


class WindowBackend:
    def __init__(self):
        """准备两个候选窗口及调用记录。"""
        self.windows = (MacOSWindowCandidate(42, 1, "Game", Rect(10, 20, 80, 60)),)
        self.raised = []

    def list_windows(self, application):
        """返回本轮窗口快照。"""
        return self.windows

    def raise_window(self, window):
        """模拟 Raise 导致窗口位置更新。"""
        self.raised.append(window)
        self.windows = (replace(window, rect=Rect(100, 200, 80, 60)),)


def test_preparation_window_query_is_read_only_and_capture_refreshes_bounds():
    """列窗口不激活，选中后激活并使用最新窗口范围。"""
    backend = WindowBackend()
    activations = []

    class Activator:
        def activate(self, application):
            """记录实际选择窗口时的激活请求。"""
            activations.append(application)

    windows = MacOSPreparationWindows(backend=backend, activator=Activator(), sleeper=lambda _: None)
    candidate = windows.list_windows("Game")[0]
    assert activations == backend.raised == []
    selected = windows.focus_window("Game", candidate.id)
    assert selected.rect == Rect(100, 200, 80, 60)
    assert selected.id == candidate.id
    assert activations == ["Game"]
    assert len(backend.raised) == 1


def test_preparation_rejects_changed_or_closed_window_without_activation():
    """同一 AX 序号的标题变化也必须使旧候选失效。"""
    backend = WindowBackend()
    windows = MacOSPreparationWindows(backend=backend)
    candidate = windows.list_windows("Game")[0]
    backend.windows = (replace(backend.windows[0], title="Other"),)
    with pytest.raises(RuntimeError, match="refresh"):
        windows.focus_window("Game", candidate.id)
    assert backend.raised == []


def test_preparation_rejects_duplicate_titles_in_one_process():
    """底层 AX Raise 按标题定位，重复标题必须显式报错。"""
    backend = WindowBackend()
    backend.windows += (replace(backend.windows[0], window_number=2),)
    windows = MacOSPreparationWindows(backend=backend)
    candidate = windows.list_windows("Game")[0]
    with pytest.raises(RuntimeError, match="same title"):
        windows.focus_window("Game", candidate.id)
    assert backend.raised == []
