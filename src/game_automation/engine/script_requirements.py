"""分析脚本执行前需要组装的运行时端口。"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.domain import ColorIs, If, Repeat, Script, Step


@dataclass(frozen=True, slots=True)
class ScriptRequirements:
    needs_color_reader: bool = False


def inspect_script_requirements(script: Script) -> ScriptRequirements:
    """递归分析脚本步骤树并返回运行时端口需求。"""
    return ScriptRequirements(needs_color_reader=_steps_need_color_reader(script.steps))


def _steps_need_color_reader(steps: tuple[Step, ...]) -> bool:
    """检查步骤序列是否包含需要颜色读取端口的条件。"""
    for step in steps:
        if isinstance(step, Repeat) and _steps_need_color_reader(step.steps):
            return True
        if isinstance(step, If) and _if_needs_color_reader(step):
            return True
    return False


def _if_needs_color_reader(step: If) -> bool:
    """检查条件分支是否直接或间接需要颜色读取端口。"""
    return (
        isinstance(step.condition, ColorIs)
        or _steps_need_color_reader(step.then_steps)
        or _steps_need_color_reader(step.else_steps)
    )
