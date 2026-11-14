"""聚合导出 macOS 应用激活 adapter。

本模块为素材准备装配提供应用激活接口，具体窗口运行能力由对应模块提供。
"""

from game_automation.platform.macos.adapters.application_activation import (
    MacOSApplicationActivator,
)

__all__ = [
    "MacOSApplicationActivator",
]
