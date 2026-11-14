"""从统一任务事实推导运行端口需求。

本模块不再解释步骤语义，也不读取文件、执行任务或选择真实 adapter。
依赖事实由领域分析提供，运行用例据此延迟创建所需端口。
"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.portable.domain.task import FunctionTask
from game_automation.portable.domain.task_analysis import analyze_task


@dataclass(frozen=True, slots=True)
class ScriptRequirements:
    """声明运行前必须提供的可选设备能力。"""

    needs_color_reader: bool = False
    needs_image_locator: bool = False
    needs_screen_state_reader: bool = False


def inspect_script_requirements(script: FunctionTask) -> ScriptRequirements:
    """从共同静态事实读取所需端口。"""
    analysis = analyze_task(script)
    return ScriptRequirements(
        needs_color_reader=analysis.uses_colors,
        needs_image_locator=bool(analysis.image_sources),
        needs_screen_state_reader=bool(analysis.state_names),
    )
