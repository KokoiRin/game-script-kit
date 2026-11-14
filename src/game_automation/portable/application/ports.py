"""定义应用用例层需要的外部环境端口。

本 module 声明素材准备使用的应用激活 seam，以及原生输入核对焦点窗口时使用的值。
它不执行平台命令、不解释任务，也不按屏幕绝对坐标绑定一次任务运行。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from game_automation.portable.domain import Rect


@dataclass(frozen=True, slots=True)
class FocusedApplicationWindow:
    """记录已绑定进程焦点窗口的标题和屏幕矩形。"""

    title: str
    rect: Rect


class ApplicationActivator(Protocol):
    """表示可把指定应用切换到可交互前台的外部能力。"""

    def activate(self, application: str) -> None:
        """激活指定应用，并在可开始准备操作时返回。"""
        ...
