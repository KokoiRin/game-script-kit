"""生成本地 UI 可展示的脚本详情。

本 module 负责把 Script 步骤树转换成只读摘要和运行前依赖检查；它不运行脚本、
不读取屏幕，也不处理 HTTP/UI 展示细节。LocalControlApplication 调用这里作为
脚本 catalog 到 UI adapter 之间的 presenter seam。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.script_dependencies import describe_script_dependencies
from game_automation.portable.domain import (
    Click,
    ColorIs,
    Drag,
    If,
    ImageExists,
    ImageRef,
    ImageSearchSpec,
    ImageTarget,
    ImageTemplate,
    OffsetTarget,
    PointRef,
    Repeat,
    ScreenStateIs,
    SearchRef,
    Script,
    Step,
    Wait,
    WaitUntil,
)


@dataclass(frozen=True, slots=True)
class ScriptDetailsResult:
    exit_code: int
    name: str
    steps: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    state_dependencies: tuple[str, ...] = ()
    point_dependencies: tuple[str, ...] = ()
    state_waits: tuple[str, ...] = ()
    state_decisions: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = ()
    image_dependencies: tuple[str, ...] = ()
    readiness: tuple[tuple[str, str, str], ...] = ()
    stderr: str = ""


def describe_script_details(
    script: Script,
    *,
    asset_root: Path,
    supported_image_suffixes: frozenset[str],
    state_names: tuple[str, ...] | None,
) -> ScriptDetailsResult:
    """生成脚本详情结果。"""
    dependency_details = describe_script_dependencies(
        script,
        asset_root=asset_root,
        supported_image_suffixes=supported_image_suffixes,
        state_names=state_names,
    )
    return ScriptDetailsResult(
        exit_code=0,
        name=script.name,
        steps=_describe_steps(script.steps),
        dependencies=dependency_details.dependencies,
        state_dependencies=dependency_details.state_dependencies,
        point_dependencies=dependency_details.point_dependencies,
        state_waits=_describe_state_waits(script.steps),
        state_decisions=_describe_state_decisions(script.steps),
        image_dependencies=dependency_details.image_dependencies,
        readiness=dependency_details.readiness,
    )


def _describe_steps(steps: tuple[Step, ...], *, indent: str = "") -> tuple[str, ...]:
    """把脚本步骤树转换成 UI 可展示的摘要行。"""
    lines: list[str] = []
    for step in steps:
        lines.extend(_describe_step(step, indent=indent))
    return tuple(lines)


def _describe_state_decisions(
    steps: tuple[Step, ...],
) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]:
    """按脚本阅读顺序收集状态条件分支摘要。"""
    decisions: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []
    for step in steps:
        _collect_state_decisions(step, decisions)
    return tuple(decisions)


def _describe_state_waits(steps: tuple[Step, ...]) -> tuple[str, ...]:
    """按脚本阅读顺序收集状态等待摘要。"""
    waits: list[str] = []
    for step in steps:
        _collect_state_waits(step, waits)
    return tuple(dict.fromkeys(waits))


def _collect_state_waits(step: Step, waits: list[str]) -> None:
    """递归收集 WaitUntil(ScreenStateIs(...)) 引用的状态。"""
    if isinstance(step, WaitUntil):
        if isinstance(step.condition, ScreenStateIs):
            waits.append(step.condition.state)
        return
    if isinstance(step, If):
        for child in (*step.then_steps, *step.else_steps):
            _collect_state_waits(child, waits)
        return
    if isinstance(step, Repeat):
        for child in step.steps:
            _collect_state_waits(child, waits)


def _collect_state_decisions(
    step: Step,
    decisions: list[tuple[str, tuple[str, ...], tuple[str, ...]]],
) -> None:
    """递归收集 If(ScreenStateIs(...)) 决策摘要。"""
    if isinstance(step, If):
        if isinstance(step.condition, ScreenStateIs):
            decisions.append(
                (
                    step.condition.state,
                    _describe_steps(step.then_steps),
                    _describe_steps(step.else_steps),
                )
            )
        for child in (*step.then_steps, *step.else_steps):
            _collect_state_decisions(child, decisions)
        return
    if isinstance(step, Repeat):
        for child in step.steps:
            _collect_state_decisions(child, decisions)


def _describe_step(step: Step, *, indent: str) -> tuple[str, ...]:
    """把单个脚本步骤转换成摘要行。"""
    if isinstance(step, Click):
        return (f"{indent}Click {_describe_target(step.point)}",)
    if isinstance(step, Drag):
        return (
            f"{indent}Drag {step.start} -> {step.end} duration={step.duration_seconds:g}s",
        )
    if isinstance(step, Wait):
        return (f"{indent}Wait {step.duration_seconds:g}s",)
    if isinstance(step, Repeat):
        return (
            f"{indent}Repeat {step.times} times",
            *_describe_steps(step.steps, indent=f"{indent}  "),
        )
    if isinstance(step, If):
        lines = [f"{indent}If {_describe_condition(step.condition)}"]
        lines.extend(f"{indent}  then {line}" for line in _describe_steps(step.then_steps))
        if step.else_steps:
            lines.extend(f"{indent}  else {line}" for line in _describe_steps(step.else_steps))
        return tuple(lines)
    if isinstance(step, WaitUntil):
        return (
            f"{indent}WaitUntil {_describe_condition(step.condition)} "
            f"timeout={step.timeout_seconds:g}s interval={step.interval_seconds:g}s",
        )
    return (f"{indent}{step}",)


def _describe_condition(condition) -> str:
    """把条件转换成接近脚本写法的摘要文本。"""
    if isinstance(condition, ScreenStateIs):
        return f'ScreenStateIs("{condition.state}")'
    if isinstance(condition, ImageExists):
        return (
            f"ImageExists({_describe_image(condition.template)}, "
            f"min_confidence={_effective_image_min_confidence(condition.min_confidence):g})"
        )
    if isinstance(condition, ColorIs):
        return f"ColorIs({condition.point}, {condition.expected})"
    return str(condition)


def _describe_target(target) -> str:
    """把点击目标转换成接近脚本写法的摘要文本。"""
    if isinstance(target, PointRef):
        return f'PointRef("{target.name}")'
    if isinstance(target, ImageTarget):
        return (
            f"ImageTarget({_describe_image(target.template)}, "
            f"min_confidence={_effective_image_min_confidence(target.min_confidence):g})"
        )
    if isinstance(target, OffsetTarget):
        return f"{_describe_target(target.base)} offset {target.offset}"
    return str(target)


def _effective_image_min_confidence(min_confidence: float | None) -> float:
    """把未显式指定的图片置信度展示为执行期默认值。"""
    return 1.0 if min_confidence is None else min_confidence


def _describe_image(image: ImageTemplate | ImageRef | ImageSearchSpec | SearchRef) -> str:
    """把图片模板、图片引用或搜索引用转换成摘要文本。"""
    if isinstance(image, ImageRef):
        return f'ImageRef("{image.name}")'
    if isinstance(image, SearchRef):
        return f'SearchRef("{image.name}")'
    if isinstance(image, ImageSearchSpec):
        return f"ImageSearchSpec({_describe_image(image.image)})"
    return image.path
