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
class ScriptTarget:
    """声明目标与显式后端，尺寸用于拒绝不适配的固定布局。"""
    application: str
    window_title: str
    width: int
    height: int
    backend: str = "desktop"

    def __post_init__(self) -> None:
        """目标文本及逻辑尺寸必须完整明确，不猜测默认窗口。"""
        if self.backend != "desktop" and not self.uses_native_window:
            raise ValueError("target backend must be desktop, macos-window or macos-window-background")
        if any(not isinstance(v,str) or not v.strip() for v in (self.application,self.window_title)):
            raise ValueError('script target requires application and window_title')
        if any(type(v) is not int or v <= 0 for v in (self.width,self.height)):
            raise ValueError('script target width and height must be positive integers')


    @property
    def uses_native_window(self) -> bool:
        """集中定义共享固定窗口会话的显式后端，避免新模式误走桌面。"""
        return self.backend in ("macos-window", "macos-window-background")


@dataclass(frozen=True, slots=True)
class Script:
    name: str
    window: Window
    steps: tuple[Step, ...]
    resources: TargetCatalog = field(default_factory=TargetCatalog)
    target: ScriptTarget | None = None

    def __post_init__(self) -> None:
        """校验脚本名称和步骤序列都可用于执行。"""
        if self.name.strip() == "":
            raise ValueError("script name cannot be empty")
        if len(self.steps) == 0:
            raise ValueError("script requires at least one step")
