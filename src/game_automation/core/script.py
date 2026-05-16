"""定义绑定单个窗口并按顺序保存动作的脚本模型。"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.core.actions import Action
from game_automation.core.windows import Window


@dataclass(frozen=True, slots=True)
class Script:
    window: Window
    actions: tuple[Action, ...]

    def __post_init__(self) -> None:
        """校验脚本至少包含一个动作，并冻结动作顺序。"""
        if len(self.actions) == 0:
            raise ValueError("script requires at least one action")
