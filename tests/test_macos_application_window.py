"""验证 macOS Accessibility 窗口读取和 Raise。"""

from __future__ import annotations

import pytest

from game_automation.platform.macos.adapters.accessibility_window_backend import (
    MacOSAccessibilityWindowBackend,
)
from game_automation.platform.macos.adapters.application_window import (
    MacOSWindowCandidate,
)
from game_automation.portable.application.ports import FocusedApplicationWindow
from game_automation.portable.domain import Rect


def test_macos_accessibility_backend_reads_and_converts_ax_windows() -> None:
    """验证 backend 读取目标应用具名窗口及其 Accessibility 矩形。"""

    class FakeAccessibility:
        kAXErrorSuccess = 0
        kAXWindowsAttribute = "windows"
        kAXTitleAttribute = "title"
        kAXMinimizedAttribute = "minimized"
        kAXPositionAttribute = "position"
        kAXSizeAttribute = "size"
        kAXValueCGPointType = "point"
        kAXValueCGSizeType = "dimensions"

        @staticmethod
        def AXUIElementCreateApplication(pid):
            """返回目标应用元素。"""
            assert pid == 42
            return "application"

        @staticmethod
        def AXUIElementCopyAttributeValue(element, attribute, output):
            """返回窗口列表、标题、位置或尺寸。"""
            values = {
                ("application", "windows"): (
                    "target-window",
                    "untitled-window",
                    "minimized-window",
                ),
                ("target-window", "minimized"): False,
                ("target-window", "title"): "Star 视觉自动化靶场",
                ("target-window", "position"): "target-position",
                ("target-window", "size"): "target-size",
                ("untitled-window", "minimized"): False,
                ("untitled-window", "title"): "",
                ("minimized-window", "minimized"): True,
            }
            return (0, values[(element, attribute)])

        @staticmethod
        def AXValueGetValue(value, value_type, output):
            """把 AXValue 替身转换为点或尺寸。"""
            values = {
                ("target-position", "point"): (100.2, 200.4),
                ("target-size", "dimensions"): (799.7, 600.1),
            }
            return (True, values[(value, value_type)])

    class FakeExecutableURL:
        @staticmethod
        def lastPathComponent():
            """返回稳定可执行文件名。"""
            return "Safari"

    class FakeRunningApplication:
        @staticmethod
        def localizedName():
            """返回本地化应用名。"""
            return "Safari浏览器"

        @staticmethod
        def bundleIdentifier():
            """返回 bundle id。"""
            return "com.apple.Safari"

        @staticmethod
        def executableURL():
            """返回可执行 URL 替身。"""
            return FakeExecutableURL()

        @staticmethod
        def processIdentifier():
            """返回应用 pid。"""
            return 42

    class FakeHelperApplication:
        @staticmethod
        def localizedName():
            """返回名称相近但不应命中的辅助进程。"""
            return "Safari Web Content"

        @staticmethod
        def bundleIdentifier():
            """返回辅助进程 bundle id。"""
            return "com.apple.Safari.WebContent"

        @staticmethod
        def executableURL():
            """返回辅助进程可执行 URL 替身。"""

            class HelperExecutableURL:
                @staticmethod
                def lastPathComponent():
                    """返回辅助进程可执行文件名。"""
                    return "Safari Web Content"

            return HelperExecutableURL()

        @staticmethod
        def processIdentifier():
            """返回辅助进程 pid。"""
            return 43

    class FakeWorkspace:
        @staticmethod
        def runningApplications():
            """返回当前运行应用。"""
            return (FakeRunningApplication(), FakeHelperApplication())

    class FakeNSWorkspace:
        @staticmethod
        def sharedWorkspace():
            """返回 workspace 替身。"""
            return FakeWorkspace()

    class FakeAppKit:
        NSWorkspace = FakeNSWorkspace

    backend = MacOSAccessibilityWindowBackend(
        accessibility=FakeAccessibility(),
        appkit=FakeAppKit(),
    )

    assert backend.list_windows("safari") == (
        MacOSWindowCandidate(42, 1, "Star 视觉自动化靶场", Rect(100, 200, 800, 600)),
    )


def test_macos_accessibility_backend_raises_matching_ax_window() -> None:
    """验证 backend 在所属进程的 Accessibility 窗口上执行 Raise。"""

    class FakeAccessibility:
        kAXErrorSuccess = 0
        kAXWindowsAttribute = "windows"
        kAXTitleAttribute = "title"
        kAXRaiseAction = "raise"

        def __init__(self) -> None:
            """初始化 AX 调用记录。"""
            self.actions = []

        def AXUIElementCreateApplication(self, pid):
            """返回可识别的应用元素。"""
            return ("application", pid)

        def AXUIElementCopyAttributeValue(self, element, attribute, output):
            """返回应用窗口列表或窗口标题。"""
            if attribute == self.kAXWindowsAttribute:
                return (0, ("other-window", "target-window"))
            titles = {
                "other-window": "其他页面",
                "target-window": "Star 视觉自动化靶场",
            }
            return (0, titles[element])

        def AXUIElementPerformAction(self, element, action):
            """记录 AX Raise 动作。"""
            self.actions.append((element, action))
            return 0

    accessibility = FakeAccessibility()
    backend = MacOSAccessibilityWindowBackend(
        accessibility=accessibility,
        appkit=object(),
    )
    candidate = MacOSWindowCandidate(
        42, 7, "Star 视觉自动化靶场", Rect(100, 200, 800, 600)
    )

    backend.raise_window(candidate)

    assert accessibility.actions == [("target-window", "raise")]


def test_macos_accessibility_backend_reports_raise_permission_failure() -> None:
    """验证 Accessibility Raise 错误会转换为平台级提示。"""

    class FailingAccessibility:
        kAXErrorSuccess = 0
        kAXWindowsAttribute = "windows"
        kAXTitleAttribute = "title"
        kAXRaiseAction = "raise"

        @staticmethod
        def AXUIElementCreateApplication(pid):
            """返回应用元素。"""
            return "application"

        @staticmethod
        def AXUIElementCopyAttributeValue(element, attribute, output):
            """返回唯一匹配窗口。"""
            if attribute == "windows":
                return (0, ("target-window",))
            return (0, "Star 视觉自动化靶场")

        @staticmethod
        def AXUIElementPerformAction(element, action):
            """模拟辅助功能权限导致 Raise 失败。"""
            return -25211

    backend = MacOSAccessibilityWindowBackend(
        accessibility=FailingAccessibility(),
        appkit=object(),
    )
    candidate = MacOSWindowCandidate(
        42, 7, "Star 视觉自动化靶场", Rect(100, 200, 800, 600)
    )

    with pytest.raises(
        RuntimeError, match="failed to raise macOS window.*Accessibility"
    ):
        backend.raise_window(candidate)


class FocusedAccessibility:
    kAXErrorSuccess = 0
    kAXFocusedWindowAttribute = "focused-window"
    kAXTitleAttribute = "title"
    kAXPositionAttribute = "position"
    kAXSizeAttribute = "size"
    kAXValueCGPointType = "point"
    kAXValueCGSizeType = "dimensions"

    def __init__(self, error=0, present=True):
        """保存固定 PID 焦点读取的系统结果。"""
        self.error, self.present = error, present
        self.calls = []

    def AXUIElementCreateApplication(self, pid):
        """仅创建明确 PID 的应用元素。"""
        self.calls.append(("application", pid))
        return ("app", pid)

    def AXUIElementCopyAttributeValue(self, element, attribute, output):
        """返回焦点窗口属性，不提供枚举或激活能力。"""
        self.calls.append((element, attribute))
        if element == ("app", 42):
            assert attribute == self.kAXFocusedWindowAttribute
            return self.error, "target" if self.present else None
        assert element == "target"
        return 0, {"title": "Game", "position": (100, 200), "size": (80, 60)}[attribute]

    def AXValueGetValue(self, value, value_type, output):
        """返回公开 AXValue 中的位置或尺寸。"""
        return True, value


def test_focused_window_read_is_bound_pid_and_geometry_without_reselection():
    """焦点读取只访问绑定应用的AXFocusedWindow及完整几何。"""

    accessibility = FocusedAccessibility()
    backend = MacOSAccessibilityWindowBackend(
        accessibility=accessibility, appkit=object()
    )
    assert backend.read_focused_window(42) == FocusedApplicationWindow(
        "Game", Rect(100, 200, 80, 60)
    )
    assert accessibility.calls == [
        ("application", 42),
        (("app", 42), "focused-window"),
        ("target", "title"),
        ("target", "position"),
        ("target", "size"),
    ]


@pytest.mark.parametrize("error,present", [(-25211, True), (0, False)])
def test_focused_window_ax_error_or_absence_is_explicit(error, present):
    """无法确认焦点窗口时明确失败，不能挑选另一扇窗口代替。"""
    backend = MacOSAccessibilityWindowBackend(
        accessibility=FocusedAccessibility(error, present), appkit=object()
    )
    with pytest.raises(RuntimeError, match="焦点窗口"):
        backend.read_focused_window(42)
