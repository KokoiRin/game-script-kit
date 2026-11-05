"""本机桌面入口 adapter 包。

本 package 承载 CLI 和本地 UI 入口；入口负责协议和界面转换，不实现脚本核心。
"""

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """兼容包级 CLI 入口，延迟导入以免准备 UI 隐式加载执行服务。"""
    from game_automation.platform.local_desktop.entrypoints.cli import main as cli_main

    return cli_main(argv)
