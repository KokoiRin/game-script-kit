"""通过 AppKit 和 Accessibility 读取并 Raise macOS 顶层窗口。

本 module 负责运行应用 pid 解析、Accessibility 属性转换和权限错误映射；
它不选择标题子串、不等待窗口稳定，也不依赖脚本或 runner。
"""

from __future__ import annotations

import platform

from game_automation.platform.macos.adapters.application_window import (
    MacOSWindowBackend,
    MacOSWindowCandidate,
)
from game_automation.portable.domain import Rect


class MacOSAccessibilityWindowBackend(MacOSWindowBackend):
    """把 AppKit 和 Accessibility framework 转换为稳定 Python 值。"""

    def __init__(
        self,
        *,
        accessibility: object | None = None,
        appkit: object | None = None,
    ) -> None:
        """加载或注入 macOS framework module。"""
        if (accessibility is None or appkit is None) and platform.system() != "Darwin":
            raise RuntimeError("macOS application window controller requires Darwin")
        if accessibility is None:
            import ApplicationServices as accessibility_module

            accessibility = accessibility_module
        if appkit is None:
            import AppKit as appkit_module

            appkit = appkit_module
        self._accessibility = accessibility
        self._appkit = appkit

    def list_windows(self, application: str) -> tuple[MacOSWindowCandidate, ...]:
        """读取目标应用 Accessibility tree 中可定位的具名顶层窗口。"""
        application_pids = self._resolve_application_pids(application)
        candidates = []
        for pid in sorted(application_pids):
            for window_index, ax_window in enumerate(self._read_ax_windows(pid), start=1):
                if self._read_ax_bool(ax_window, self._accessibility.kAXMinimizedAttribute):
                    continue
                title = self._read_ax_text(ax_window, self._accessibility.kAXTitleAttribute)
                if not title:
                    continue
                rect = self._read_ax_window_rect(ax_window)
                if rect is None:
                    continue
                candidates.append(
                    MacOSWindowCandidate(
                        pid=pid,
                        window_number=window_index,
                        title=title,
                        rect=rect,
                    )
                )
        return tuple(candidates)

    def raise_window(self, window: MacOSWindowCandidate) -> None:
        """在窗口所属进程的 Accessibility tree 中找到同名窗口并 Raise。"""
        accessibility = self._accessibility
        for ax_window in self._read_ax_windows(window.pid):
            title_error, title = accessibility.AXUIElementCopyAttributeValue(
                ax_window,
                accessibility.kAXTitleAttribute,
                None,
            )
            if title_error != accessibility.kAXErrorSuccess or str(title) != window.title:
                continue
            raise_error = accessibility.AXUIElementPerformAction(
                ax_window,
                accessibility.kAXRaiseAction,
            )
            if raise_error != accessibility.kAXErrorSuccess:
                raise _raise_error(window.title)
            return
        raise _raise_error(window.title)

    def _read_ax_windows(self, pid: int) -> tuple[object, ...]:
        """读取一个应用进程的 Accessibility 顶层窗口列表。"""
        accessibility = self._accessibility
        application_element = accessibility.AXUIElementCreateApplication(pid)
        error, windows = accessibility.AXUIElementCopyAttributeValue(
            application_element,
            accessibility.kAXWindowsAttribute,
            None,
        )
        if error != accessibility.kAXErrorSuccess:
            raise RuntimeError(
                "failed to read macOS application windows. "
                "Check Accessibility permission for the Python runtime."
            )
        return tuple(windows or ())

    def _read_ax_text(self, element: object, attribute: object) -> str:
        """读取可空 Accessibility 文本属性。"""
        error, value = self._accessibility.AXUIElementCopyAttributeValue(
            element,
            attribute,
            None,
        )
        if error != self._accessibility.kAXErrorSuccess or value is None:
            return ""
        return str(value).strip()

    def _read_ax_bool(self, element: object, attribute: object) -> bool:
        """读取可选 Accessibility 布尔属性，缺失时按 false 处理。"""
        error, value = self._accessibility.AXUIElementCopyAttributeValue(
            element,
            attribute,
            None,
        )
        return error == self._accessibility.kAXErrorSuccess and bool(value)

    def _read_ax_window_rect(self, ax_window: object) -> Rect | None:
        """读取 Accessibility 窗口的位置和尺寸并转换为 Rect。"""
        accessibility = self._accessibility
        position_error, position_value = accessibility.AXUIElementCopyAttributeValue(
            ax_window,
            accessibility.kAXPositionAttribute,
            None,
        )
        size_error, size_value = accessibility.AXUIElementCopyAttributeValue(
            ax_window,
            accessibility.kAXSizeAttribute,
            None,
        )
        if (
            position_error != accessibility.kAXErrorSuccess
            or size_error != accessibility.kAXErrorSuccess
        ):
            return None
        position = _read_ax_pair(
            accessibility,
            position_value,
            accessibility.kAXValueCGPointType,
            first_name="x",
            second_name="y",
        )
        size = _read_ax_pair(
            accessibility,
            size_value,
            accessibility.kAXValueCGSizeType,
            first_name="width",
            second_name="height",
        )
        if position is None or size is None:
            return None
        try:
            return Rect(
                left=round(position[0]),
                top=round(position[1]),
                width=round(size[0]),
                height=round(size[1]),
            )
        except ValueError:
            return None

    def _resolve_application_pids(self, application: str) -> frozenset[int]:
        """按本地化名、bundle id 或可执行文件名解析运行应用 pid。"""
        requested = application.casefold()
        running_applications = self._appkit.NSWorkspace.sharedWorkspace().runningApplications()
        pids = []
        for running_application in running_applications:
            names = (
                _optional_objc_text(running_application, "localizedName"),
                _optional_objc_text(running_application, "bundleIdentifier"),
                _running_application_executable_name(running_application),
            )
            if any(_application_name_matches(name, requested) for name in names if name):
                pids.append(int(_objc_value(running_application, "processIdentifier")))
        return frozenset(pids)


def _read_ax_pair(
    accessibility: object,
    value: object,
    value_type: object,
    *,
    first_name: str,
    second_name: str,
) -> tuple[float, float] | None:
    """把 AXValue 中的 CGPoint 或 CGSize 归一化为两个浮点数。"""
    converted = accessibility.AXValueGetValue(value, value_type, None)
    if (
        isinstance(converted, tuple)
        and len(converted) == 2
        and isinstance(converted[0], bool)
    ):
        success, converted = converted
        if not success:
            return None
    if hasattr(converted, first_name) and hasattr(converted, second_name):
        return (
            float(getattr(converted, first_name)),
            float(getattr(converted, second_name)),
        )
    if isinstance(converted, tuple | list) and len(converted) == 2:
        return (float(converted[0]), float(converted[1]))
    return None


def _objc_value(instance: object, attribute: str) -> object:
    """兼容读取 PyObjC 无参方法或测试替身属性。"""
    value = getattr(instance, attribute)
    return value() if callable(value) else value


def _optional_objc_text(instance: object, attribute: str) -> str:
    """读取可空 PyObjC 文本属性并归一化为空字符串。"""
    value = _objc_value(instance, attribute)
    return "" if value is None else str(value)


def _running_application_executable_name(running_application: object) -> str:
    """读取运行应用可执行文件名，缺失 URL 时返回空字符串。"""
    executable_url = _objc_value(running_application, "executableURL")
    if executable_url is None:
        return ""
    return _optional_objc_text(executable_url, "lastPathComponent")


def _application_name_matches(name: str, requested: str) -> bool:
    """精确匹配主应用标识，避免把 Web Content 等辅助进程纳入。"""
    return name.casefold() == requested


def _raise_error(title: str) -> RuntimeError:
    """构造稳定的 macOS 窗口 Raise 权限错误。"""
    return RuntimeError(
        f"failed to raise macOS window '{title}'. "
        "Check Accessibility permission for the Python runtime."
    )
