"""定义素材准备使用的 macOS 窗口候选。

本 module 只保存候选值和 backend 协议；它不按屏幕坐标绑定任务运行，
也不激活应用或解释图片搜索。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from game_automation.portable.domain import Rect


@dataclass(frozen=True, slots=True)
class MacOSWindowCandidate:
    """保存 macOS backend 返回的顶层窗口信息。"""

    pid: int
    window_number: int
    title: str
    rect: Rect


class MacOSWindowBackend(Protocol):
    """隔离 macOS framework 类型，便于控制器行为测试。"""

    def list_windows(self, application: str) -> tuple[MacOSWindowCandidate, ...]:
        """列出指定应用当前可见的具名顶层窗口。"""
        ...

    def raise_window(self, window: MacOSWindowCandidate) -> None:
        """通过平台能力 Raise 指定窗口。"""
        ...
