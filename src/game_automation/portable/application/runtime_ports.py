"""定义一次真实运行独占的端口集合与生命周期边界。

应用层拥有会话的开启和关闭；平台工厂负责创建共享资源，不改变 runner 的坐标契约。
本模块不导入平台实现，也不为显式后端选择提供隐式回退。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ContextManager, Protocol

from game_automation.portable.domain.windows import Window
from game_automation.portable.domain.script import ScriptTarget
from game_automation.portable.engine.ports import CancellationToken, InputDevice, RuntimeControl, PixelColorReader, RunLogger, ScreenImageLocator, ScreenStateReader
from game_automation.portable.engine.script_requirements import ScriptRequirements


@dataclass(frozen=True, slots=True)
class RuntimePorts:
    """聚合本次运行共享同一窗口与图像源的端口。"""
    window: Window
    device: InputDevice
    color_reader: PixelColorReader | None = None
    image_locator: ScreenImageLocator | None = None
    screen_state_reader: ScreenStateReader | None = None
    control: RuntimeControl | None = None


class RuntimeFactory(Protocol):
    def open(self, target: ScriptTarget, requirements: ScriptRequirements,
             cancellation: CancellationToken | None, logger: RunLogger | None) -> ContextManager[RuntimePorts]:
        """打开一轮独占会话，退出时必须完成资源停止。"""
        ...
