"""验证 macOS 顶层窗口选择、矩形读取和 Accessibility Raise。"""

from __future__ import annotations

import pytest

from game_automation.platform.macos.adapters.accessibility_window_backend import (
    MacOSAccessibilityWindowBackend,
)
from game_automation.platform.macos.adapters.application_window import (
    MacOSApplicationWindowController,
    MacOSWindowCandidate,
)
from game_automation.portable.application.ports import FocusedApplicationWindow
from game_automation.portable.domain import Rect


class FakeWindowBackend:
    """提供可控候选窗口和 Raise 记录。"""

    def __init__(self, windows: tuple[MacOSWindowCandidate, ...]) -> None:
        """初始化候选窗口集合。"""
        self.windows = windows
        self.calls = []

    def list_windows(self, application: str) -> tuple[MacOSWindowCandidate, ...]:
        """记录应用查询并返回候选窗口。"""
        self.calls.append(("list", application))
        return self.windows

    def raise_window(self, window: MacOSWindowCandidate) -> None:
        """记录目标窗口 Raise。"""
        self.calls.append(("raise", window))


def test_macos_window_controller_focuses_unique_title_match() -> None:
    """验证控制器按不区分大小写的标题子串选择唯一窗口。"""
    target = MacOSWindowCandidate(42, 7, "Star 视觉自动化靶场", Rect(100, 200, 800, 600))
    backend = FakeWindowBackend(
        (
            MacOSWindowCandidate(42, 6, "其他页面", Rect(0, 0, 400, 300)),
            target,
        )
    )
    waits = []
    controller = MacOSApplicationWindowController(
        backend=backend,
        sleeper=waits.append,
        stabilization_seconds=0.2,
    )

    result = controller.focus_window("Safari", "STAR 视觉自动化")

    assert result == FocusedApplicationWindow(target.title, target.rect)
    assert backend.calls == [("list", "Safari"), ("raise", target)]
    assert waits == [0.2]


def test_macos_window_controller_rejects_missing_title() -> None:
    """验证没有匹配窗口时返回可读错误。"""
    controller = MacOSApplicationWindowController(
        backend=FakeWindowBackend(()),
        sleeper=lambda _: None,
    )

    with pytest.raises(RuntimeError, match="target window containing 'Missing' was not found"):
        controller.focus_window("Safari", "Missing")


def test_macos_window_controller_rejects_ambiguous_title() -> None:
    """验证多个窗口匹配时要求更具体的标题。"""
    backend = FakeWindowBackend(
        (
            MacOSWindowCandidate(42, 6, "Star - A", Rect(0, 0, 400, 300)),
            MacOSWindowCandidate(42, 7, "Star - B", Rect(10, 20, 400, 300)),
        )
    )
    controller = MacOSApplicationWindowController(backend=backend, sleeper=lambda _: None)

    with pytest.raises(RuntimeError, match="matched multiple windows.*more specific"):
        controller.focus_window("Safari", "Star")


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
    candidate = MacOSWindowCandidate(42, 7, "Star 视觉自动化靶场", Rect(100, 200, 800, 600))

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
    candidate = MacOSWindowCandidate(42, 7, "Star 视觉自动化靶场", Rect(100, 200, 800, 600))

    with pytest.raises(RuntimeError, match="failed to raise macOS window.*Accessibility"):
        backend.raise_window(candidate)
