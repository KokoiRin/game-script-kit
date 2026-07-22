"""定义应用用例层需要的外部环境端口。

本 module 只声明真实运行前的应用环境准备 seam；它不执行平台命令、
不解释脚本步骤，也不决定入口参数如何解析。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from game_automation.portable.domain import Rect


class ApplicationActivator(Protocol):
    """表示可把指定应用切换到可交互前台的外部能力。"""

    def activate(self, application: str) -> None:
        """激活指定应用，并在可开始自动化操作时返回。"""
        ...


@dataclass(frozen=True, slots=True)
class FocusedApplicationWindow:
    """记录平台已选中窗口的标题和屏幕矩形。"""

    title: str
    rect: Rect


class ApplicationWindowController(Protocol):
    """表示可按应用和标题选择顶层窗口的外部能力。"""

    def focus_window(
        self,
        application: str,
        title_contains: str,
    ) -> FocusedApplicationWindow:
        """Raise 唯一匹配窗口并返回其当前屏幕范围。"""
        ...
