"""分析脚本详情中的外部依赖和运行前检查。

本 module 负责从 Script 步骤树提取可展示依赖、结构化状态/图片依赖和 readiness；
它不生成步骤摘要、不运行脚本，也不处理 HTTP/UI 展示细节。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.domain import (
    Click,
    ColorIs,
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
    WaitUntil,
)


@dataclass(frozen=True, slots=True)
class ScriptDependencyDetails:
    dependencies: tuple[str, ...] = ()
    state_dependencies: tuple[str, ...] = ()
    image_dependencies: tuple[str, ...] = ()
    readiness: tuple[tuple[str, str, str], ...] = ()


def describe_script_dependencies(
    script: Script,
    *,
    asset_root: Path,
    supported_image_suffixes: frozenset[str],
    state_names: tuple[str, ...] | None,
) -> ScriptDependencyDetails:
    """生成脚本依赖摘要、结构化依赖和运行前检查。"""
    dependencies = _describe_dependencies(script.steps)
    return ScriptDependencyDetails(
        dependencies=dependencies,
        state_dependencies=_collect_state_dependencies(script.steps),
        image_dependencies=_collect_image_dependencies(script.steps, resources=script.resources),
        readiness=_describe_readiness(
            script.steps,
            dependencies=dependencies,
            resources=script.resources,
            asset_root=asset_root,
            supported_image_suffixes=supported_image_suffixes,
            state_names=state_names,
        ),
    )


def _describe_dependencies(steps: tuple[Step, ...]) -> tuple[str, ...]:
    """收集脚本运行前最值得用户检查的外部依赖。"""
    dependencies: list[str] = []
    for step in steps:
        _collect_step_dependencies(step, dependencies)
    return tuple(dict.fromkeys(dependencies))


def _describe_readiness(
    steps: tuple[Step, ...],
    *,
    dependencies: tuple[str, ...],
    resources: TargetCatalog,
    asset_root: Path,
    supported_image_suffixes: frozenset[str],
    state_names: tuple[str, ...] | None,
) -> tuple[tuple[str, str, str], ...]:
    """生成脚本详情中的运行前依赖检查结果。"""
    checks = []
    for dependency in dependencies:
        if dependency.startswith("状态: "):
            checks.append(_screen_state_readiness(dependency, state_names=state_names))
    checks.extend(
        _image_readiness(
            dependency,
            asset_root=asset_root,
            supported_image_suffixes=supported_image_suffixes,
        )
        for dependency in _collect_image_readiness_dependencies(steps, resources=resources)
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


@dataclass(frozen=True, slots=True)
class _ImageReadinessDependency:
    label: str
    template: ImageTemplate | None
    named: bool = False


def _collect_image_readiness_dependencies(
    steps: tuple[Step, ...],
    *,
    resources: TargetCatalog,
) -> tuple[_ImageReadinessDependency, ...]:
    """按脚本阅读顺序收集图片依赖检查项。"""
    dependencies: list[_ImageReadinessDependency] = []
    for step in steps:
        _collect_step_image_readiness_dependencies(step, dependencies, resources=resources)
    return tuple(dict.fromkeys(dependencies))


def _collect_step_image_readiness_dependencies(
    step: Step,
    dependencies: list[_ImageReadinessDependency],
    *,
    resources: TargetCatalog,
) -> None:
    """收集单个步骤内图片依赖检查项。"""
    if isinstance(step, Click):
        _collect_target_image_readiness_dependencies(step.point, dependencies, resources=resources)
        return
    if isinstance(step, If):
        _collect_condition_image_readiness_dependencies(step.condition, dependencies, resources=resources)
        for child in (*step.then_steps, *step.else_steps):
            _collect_step_image_readiness_dependencies(child, dependencies, resources=resources)
        return
    if isinstance(step, Repeat):
        for child in step.steps:
            _collect_step_image_readiness_dependencies(child, dependencies, resources=resources)
        return
    if isinstance(step, WaitUntil):
        _collect_condition_image_readiness_dependencies(step.condition, dependencies, resources=resources)


def _collect_condition_image_readiness_dependencies(
    condition,
    dependencies: list[_ImageReadinessDependency],
    *,
    resources: TargetCatalog,
) -> None:
    """收集条件中的图片依赖检查项。"""
    if isinstance(condition, ImageExists):
        dependencies.append(_image_readiness_dependency(condition.template, resources=resources))


def _collect_target_image_readiness_dependencies(
    target,
    dependencies: list[_ImageReadinessDependency],
    *,
    resources: TargetCatalog,
) -> None:
    """收集点击目标中的图片依赖检查项。"""
    if isinstance(target, ImageTarget):
        dependencies.append(_image_readiness_dependency(target.template, resources=resources))
        return
    if isinstance(target, OffsetTarget):
        _collect_target_image_readiness_dependencies(target.base, dependencies, resources=resources)


def _image_readiness_dependency(
    image: ImageTemplate | ImageRef,
    *,
    resources: TargetCatalog,
) -> _ImageReadinessDependency:
    """把图片引用转换成依赖检查项。"""
    label = f"图片: {_describe_image(image)}"
    if isinstance(image, ImageRef):
        try:
            return _ImageReadinessDependency(
                label=label,
                template=resources.resolve_image(image),
                named=True,
            )
        except LookupError:
            return _ImageReadinessDependency(label=label, template=None, named=True)
    return _ImageReadinessDependency(label=label, template=image)


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
    dependency: _ImageReadinessDependency,
    *,
    asset_root: Path,
    supported_image_suffixes: frozenset[str],
) -> tuple[str, str, str]:
    """检查脚本引用的 assets 图片是否存在。"""
    if dependency.template is None:
        return dependency.label, "missing", "命名图片未配置"
    image_path = Path(dependency.template.path)
    if (
        image_path.is_absolute()
        or image_path.parts[:1] != (asset_root.name,)
        or ".." in image_path.parts
    ):
        return dependency.label, "unknown", "图片不在项目 assets 目录，无法确认"
    candidate = (asset_root.parent / image_path).resolve()
    resolved_asset_root = asset_root.resolve()
    try:
        candidate.relative_to(resolved_asset_root)
    except ValueError:
        return dependency.label, "unknown", "图片不在项目 assets 目录，无法确认"
    if candidate.is_file() and candidate.suffix.lower() in supported_image_suffixes:
        if dependency.named:
            return dependency.label, "ok", f"命名图片已配置，图片文件可用：{dependency.template.path}"
        return dependency.label, "ok", "图片文件可用"
    if dependency.named:
        return dependency.label, "missing", f"命名图片已配置，但图片文件不存在或后缀不受支持：{dependency.template.path}"
    return dependency.label, "missing", "图片文件不存在或后缀不受支持"


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


def _describe_image(image: ImageTemplate | ImageRef) -> str:
    """把图片模板或图片引用转换成摘要文本。"""
    if isinstance(image, ImageRef):
        return f'ImageRef("{image.name}")'
    return image.path
