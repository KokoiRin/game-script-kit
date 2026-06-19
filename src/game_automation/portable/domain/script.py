"""定义绑定单个窗口并按顺序保存步骤树的脚本模型。

本 module 只描述一份脚本的名称、窗口和步骤树；它不查找脚本、不执行步骤，
也不关心 dry-run 或真实运行模式。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_automation.portable.domain.actions import Step
from game_automation.portable.domain.point_aliases import TargetCatalog
from game_automation.portable.domain.windows import Window


@dataclass(frozen=True, slots=True)
class Script:
    name: str
    window: Window
    steps: tuple[Step, ...]
    resources: TargetCatalog = field(default_factory=TargetCatalog)

    def __post_init__(self) -> None:
        """校验脚本名称和步骤序列都可用于执行。"""
        if self.name.strip() == "":
            raise ValueError("script name cannot be empty")
        if len(self.steps) == 0:
            raise ValueError("script requires at least one step")
