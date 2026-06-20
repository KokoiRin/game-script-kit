"""生成本地 UI 可展示的脚本详情。

本 module 负责把 Script 步骤树转换成只读摘要和运行前依赖检查；它不运行脚本、
不读取屏幕，也不处理 HTTP/UI 展示细节。LocalControlApplication 调用这里作为
脚本 catalog 到 UI adapter 之间的 presenter seam。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.domain import (
    Click,
    ColorIs,
    Drag,
    If,
    ImageExists,
    ImageRef,
    ImageTarget,
    ImageTemplate,
    OffsetTarget,
    PointRef,
    Repeat,
    ScreenStateIs,
    Script,
    Step,
    TargetCatalog,
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
    return ScriptDetailsResult(
        exit_code=0,
        name=script.name,
        steps=_describe_steps(script.steps),
        dependencies=_describe_dependencies(script.steps),
        state_dependencies=_collect_state_dependencies(script.steps),
        image_dependencies=_collect_image_dependencies(script.steps, resources=script.resources),
        readiness=_describe_readiness(
            script.steps,
            asset_root=asset_root,
            supported_image_suffixes=supported_image_suffixes,
            state_names=state_names,
        ),
    )


def _describe_steps(steps: tuple[Step, ...], *, indent: str = "") -> tuple[str, ...]:
    """把脚本步骤树转换成 UI 可展示的摘要行。"""
    lines: list[str] = []
    for step in steps:
        lines.extend(_describe_step(step, indent=indent))
    return tuple(lines)


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
        return f"ImageExists({_describe_image(condition.template)}, min_confidence={condition.min_confidence:g})"
    if isinstance(condition, ColorIs):
        return f"ColorIs({condition.point}, {condition.expected})"
    return str(condition)


def _describe_target(target) -> str:
    """把点击目标转换成接近脚本写法的摘要文本。"""
    if isinstance(target, PointRef):
        return f'PointRef("{target.name}")'
    if isinstance(target, ImageTarget):
        return f"ImageTarget({_describe_image(target.template)}, min_confidence={target.min_confidence:g})"
    if isinstance(target, OffsetTarget):
        return f"{_describe_target(target.base)} offset {target.offset}"
    return str(target)


def _describe_image(image: ImageTemplate | ImageRef) -> str:
    """把图片模板或图片引用转换成摘要文本。"""
    if isinstance(image, ImageRef):
        return f'ImageRef("{image.name}")'
    return image.path


def _describe_dependencies(steps: tuple[Step, ...]) -> tuple[str, ...]:
    """收集脚本运行前最值得用户检查的外部依赖。"""
    dependencies: list[str] = []
    for step in steps:
        _collect_step_dependencies(step, dependencies)
    return tuple(dict.fromkeys(dependencies))


def _describe_readiness(
    steps: tuple[Step, ...],
    *,
    asset_root: Path,
    supported_image_suffixes: frozenset[str],
    state_names: tuple[str, ...] | None,
) -> tuple[tuple[str, str, str], ...]:
    """生成脚本详情中的运行前依赖检查结果。"""
    checks = []
    for dependency in _describe_dependencies(steps):
        if dependency.startswith("状态: "):
            checks.append(_screen_state_readiness(dependency, state_names=state_names))
        elif dependency.startswith("图片: "):
            checks.append(
                _image_readiness(
                    dependency,
                    asset_root=asset_root,
                    supported_image_suffixes=supported_image_suffixes,
                )
            )
    return tuple(dict.fromkeys(checks))


def _collect_state_dependencies(steps: tuple[Step, ...]) -> tuple[str, ...]:
    """按脚本阅读顺序收集去重后的界面状态依赖。"""
    states: list[str] = []
    for step in steps:
        _collect_step_state_dependencies(step, states)
    return tuple(dict.fromkeys(states))


def _collect_step_state_dependencies(step: Step, states: list[str]) -> None:
    """收集单个步骤内直接或嵌套条件引用的界面状态。"""
    if isinstance(step, If):
        _collect_condition_state_dependencies(step.condition, states)
        for child in (*step.then_steps, *step.else_steps):
            _collect_step_state_dependencies(child, states)
        return
    if isinstance(step, Repeat):
        for child in step.steps:
            _collect_step_state_dependencies(child, states)
        return
    if isinstance(step, WaitUntil):
        _collect_condition_state_dependencies(step.condition, states)


def _collect_condition_state_dependencies(condition, states: list[str]) -> None:
    """收集条件中的界面状态依赖。"""
    if isinstance(condition, ScreenStateIs):
        states.append(condition.state)


def _collect_image_dependencies(
    steps: tuple[Step, ...],
    *,
    resources: TargetCatalog,
) -> tuple[str, ...]:
    """按脚本阅读顺序收集可直接传给 dry-run 的图片模板路径。"""
    images: list[str] = []
    for step in steps:
        _collect_step_image_dependencies(step, images, resources=resources)
    return tuple(dict.fromkeys(images))


def _collect_step_image_dependencies(
    step: Step,
    images: list[str],
    *,
    resources: TargetCatalog,
) -> None:
    """收集单个步骤内直接或嵌套引用的图片模板路径。"""
    if isinstance(step, Click):
        _collect_target_image_dependencies(step.point, images, resources=resources)
        return
    if isinstance(step, If):
        _collect_condition_image_dependencies(step.condition, images, resources=resources)
        for child in (*step.then_steps, *step.else_steps):
            _collect_step_image_dependencies(child, images, resources=resources)
        return
    if isinstance(step, Repeat):
        for child in step.steps:
            _collect_step_image_dependencies(child, images, resources=resources)
        return
    if isinstance(step, WaitUntil):
        _collect_condition_image_dependencies(step.condition, images, resources=resources)


def _collect_condition_image_dependencies(
    condition,
    images: list[str],
    *,
    resources: TargetCatalog,
) -> None:
    """收集条件中的图片模板路径。"""
    if isinstance(condition, ImageExists):
        _append_resolved_image_dependency(condition.template, images, resources=resources)


def _collect_target_image_dependencies(
    target,
    images: list[str],
    *,
    resources: TargetCatalog,
) -> None:
    """收集点击目标中的图片模板路径。"""
    if isinstance(target, ImageTarget):
        _append_resolved_image_dependency(target.template, images, resources=resources)
        return
    if isinstance(target, OffsetTarget):
        _collect_target_image_dependencies(target.base, images, resources=resources)


def _append_resolved_image_dependency(
    image: ImageTemplate | ImageRef,
    images: list[str],
    *,
    resources: TargetCatalog,
) -> None:
    """把直接模板或可解析命名图片追加为 dry-run 可用路径。"""
    try:
        images.append(resources.resolve_image(image).path)
    except LookupError:
        return


def _screen_state_readiness(
    dependency: str,
    *,
    state_names: tuple[str, ...] | None,
) -> tuple[str, str, str]:
    """检查脚本引用的界面状态是否能从配置中确认。"""
    state = dependency.removeprefix("状态: ")
    if state_names is None:
        return dependency, "unknown", "状态配置不可用，无法确认"
    if state in state_names:
        return dependency, "ok", "状态已配置"
    return dependency, "missing", "状态未配置"


def _image_readiness(
    dependency: str,
    *,
    asset_root: Path,
    supported_image_suffixes: frozenset[str],
) -> tuple[str, str, str]:
    """检查脚本引用的 assets 图片是否存在。"""
    image = dependency.removeprefix("图片: ")
    image_path = Path(image)
    if (
        image_path.is_absolute()
        or image_path.parts[:1] != (asset_root.name,)
        or ".." in image_path.parts
    ):
        return dependency, "unknown", "图片不在项目 assets 目录，无法确认"
    candidate = (asset_root.parent / image_path).resolve()
    resolved_asset_root = asset_root.resolve()
    try:
        candidate.relative_to(resolved_asset_root)
    except ValueError:
        return dependency, "unknown", "图片不在项目 assets 目录，无法确认"
    if candidate.is_file() and candidate.suffix.lower() in supported_image_suffixes:
        return dependency, "ok", "图片文件可用"
    return dependency, "missing", "图片文件不存在或后缀不受支持"


def _collect_step_dependencies(step: Step, dependencies: list[str]) -> None:
    """收集单个步骤涉及的状态、图片、点位和颜色依赖。"""
    if isinstance(step, Click):
        _collect_target_dependencies(step.point, dependencies)
        return
    if isinstance(step, If):
        _collect_condition_dependencies(step.condition, dependencies)
        for child in (*step.then_steps, *step.else_steps):
            _collect_step_dependencies(child, dependencies)
        return
    if isinstance(step, Repeat):
        for child in step.steps:
            _collect_step_dependencies(child, dependencies)
        return
    if isinstance(step, WaitUntil):
        _collect_condition_dependencies(step.condition, dependencies)


def _collect_condition_dependencies(condition, dependencies: list[str]) -> None:
    """收集条件中涉及的外部依赖。"""
    if isinstance(condition, ScreenStateIs):
        dependencies.append(f"状态: {condition.state}")
        return
    if isinstance(condition, ImageExists):
        dependencies.append(f"图片: {_describe_image(condition.template)}")
        return
    if isinstance(condition, ColorIs):
        dependencies.append(f"颜色: {condition.expected} @ {condition.point}")


def _collect_target_dependencies(target, dependencies: list[str]) -> None:
    """收集点击目标中涉及的外部依赖。"""
    if isinstance(target, PointRef):
        dependencies.append(f"点位: {target.name}")
        return
    if isinstance(target, ImageTarget):
        dependencies.append(f"图片: {_describe_image(target.template)}")
        return
    if isinstance(target, OffsetTarget):
        _collect_target_dependencies(target.base, dependencies)
