"""静态分析脚本执行前需要组装的运行时端口。

本 module 只从脚本步骤树推导端口需求；它不创建端口、不执行脚本，
也不决定 dry-run 或真实 adapter 的选择。
"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.portable.domain import (
    Click,
    ColorIs,
    If,
    ImageExists,
    ImageTarget,
    Repeat,
    Script,
    Step,
    WaitUntil,
)
from game_automation.portable.domain.conditions import Condition


@dataclass(frozen=True, slots=True)
class ScriptRequirements:
    needs_color_reader: bool = False
    needs_image_locator: bool = False


def inspect_script_requirements(script: Script) -> ScriptRequirements:
    """递归分析脚本步骤树并返回运行时端口需求。"""
    return _inspect_steps(script.steps)


def _inspect_steps(steps: tuple[Step, ...]) -> ScriptRequirements:
    """检查步骤序列需要哪些运行时端口。"""
    needs_color_reader = False
    needs_image_locator = False
    for step in steps:
        requirements = _inspect_step(step)
        needs_color_reader = needs_color_reader or requirements.needs_color_reader
        needs_image_locator = needs_image_locator or requirements.needs_image_locator
    return ScriptRequirements(
        needs_color_reader=needs_color_reader,
        needs_image_locator=needs_image_locator,
    )


def _inspect_step(step: Step) -> ScriptRequirements:
    """检查单个步骤直接或间接需要哪些端口。"""
    if isinstance(step, Click) and isinstance(step.point, ImageTarget):
        return ScriptRequirements(needs_image_locator=True)
    if isinstance(step, Repeat):
        return _inspect_steps(step.steps)
    if isinstance(step, If):
        return _merge_requirements(
            _inspect_condition(step.condition),
            _inspect_steps(step.then_steps),
            _inspect_steps(step.else_steps),
        )
    if isinstance(step, WaitUntil):
        return _inspect_condition(step.condition)
    return ScriptRequirements()


def _inspect_condition(condition: Condition) -> ScriptRequirements:
    """检查条件自身需要哪些运行时端口。"""
    return ScriptRequirements(
        needs_color_reader=isinstance(condition, ColorIs),
        needs_image_locator=isinstance(condition, ImageExists),
    )


def _merge_requirements(*requirements: ScriptRequirements) -> ScriptRequirements:
    """合并多段步骤或条件的端口需求。"""
    return ScriptRequirements(
        needs_color_reader=any(item.needs_color_reader for item in requirements),
        needs_image_locator=any(item.needs_image_locator for item in requirements),
    )
