"""本机桌面入口 adapter 包。

本 package 承载 CLI 和本地 UI 入口；入口负责协议和界面转换，不实现脚本核心。
"""

from game_automation.platform.local_desktop.entrypoints.cli import main

__all__ = ["main"]
