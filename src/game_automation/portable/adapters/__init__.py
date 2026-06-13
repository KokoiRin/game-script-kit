"""平台无关 adapter 包。

本 package 承载 dry-run 这类不绑定具体操作系统的 adapter；真实桌面和系统能力
实现放在 platform/ 下。
"""

from game_automation.portable.adapters.dry_run import DryRunInputDevice, DryRunPixelColorReader

__all__ = ["DryRunInputDevice", "DryRunPixelColorReader"]
