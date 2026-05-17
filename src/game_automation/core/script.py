"""定义绑定单个窗口并按顺序保存动作的脚本模型。"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.core.actions import Action
from game_automation.core.windows import Window


@dataclass(frozen=True, slots=True)
class Script:
    name: str
    window: Window
    actions: tuple[Action, ...]

    def __post_init__(self) -> None:
        """校验脚本名称和动作序列都可用于执行。"""
        if self.name.strip() == "":
            raise ValueError("script name cannot be empty")
        if len(self.actions) == 0:
            raise ValueError("script requires at least one action")
