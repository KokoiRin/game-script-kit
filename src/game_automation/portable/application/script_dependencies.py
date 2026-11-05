"""静态分析脚本资源引用、运行前校验和详情依赖。

本 module 负责解析步骤树中的资源引用、判断共享资源需求并生成 readiness；
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
    TargetCatalog,
    WaitUntil,
)
from game_automation.portable.domain.point_aliases import (
    UnknownImageNameError,
    UnknownImageSearchNameError,
    UnknownPointNameError,
    UnknownRegionNameError,
)


ImageDependencySource = ImageTemplate | ImageRef | ImageSearchSpec | SearchRef


@dataclass(frozen=True, slots=True)
class ScriptDependencyDetails:
    dependencies: tuple[str, ...] = ()
    state_dependencies: tuple[str, ...] = ()
    point_dependencies: tuple[str, ...] = ()
    image_dependencies: tuple[str, ...] = ()
    readiness: tuple[tuple[str, str, str], ...] = ()


def validate_script_resource_references(script: Script) -> None:
    """执行前解析全部分支的资源引用，不读取桌面或要求模拟模板文件存在。"""
    for name in _collect_point_dependencies(script.steps):
        script.resources.resolve_point(PointRef(name))
    for image in _collect_image_sources(script.steps):
        _resolve_image_dependency_template(image, resources=script.resources)


def script_needs_shared_resources(script: Script) -> bool:
    """仅在脚本引用的搜索或区域无法由局部资源解析时请求共享配置。"""
    for image in _collect_image_sources(script.steps):
        if isinstance(image, ImageSearchSpec | SearchRef):
            try:
                script.resources.resolve_search(image)
            except (UnknownImageSearchNameError, UnknownRegionNameError):
                return True
            except UnknownImageNameError:
                # 状态配置不提供命名图片，缺失的局部图片由预检查报告。
                continue
    return False


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
        point_dependencies=_collect_point_dependencies(script.steps),
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
    for name in _collect_point_dependencies(steps):
        try:
            resources.resolve_point(PointRef(name))
        except UnknownPointNameError:
            checks.append((f"点位: {name}", "missing", "命名点位未配置"))
        else:
            checks.append((f"点位: {name}", "ok", "点位已配置"))
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
        _collect_condition_state_dependencies(step.break_if, states)
        for child in step.steps:
            _collect_step_state_dependencies(child, states)
        return
    if isinstance(step, WaitUntil):
        _collect_condition_state_dependencies(step.condition, states)


def _collect_condition_state_dependencies(condition, states: list[str]) -> None:
    """收集条件中的界面状态依赖。"""
    if isinstance(condition, ScreenStateIs):
        states.append(condition.state)


def _collect_point_dependencies(steps: tuple[Step, ...]) -> tuple[str, ...]:
    """按脚本阅读顺序收集去重后的命名点位依赖。"""
    points: list[str] = []
    for step in steps:
        _collect_step_point_dependencies(step, points)
    return tuple(dict.fromkeys(points))


def _collect_step_point_dependencies(step: Step, points: list[str]) -> None:
    """收集单个步骤内直接或嵌套点击目标引用的命名点位。"""
    if isinstance(step, Click):
        _collect_target_point_dependencies(step.point, points)
        return
    if isinstance(step, If):
        for child in (*step.then_steps, *step.else_steps):
            _collect_step_point_dependencies(child, points)
        return
    if isinstance(step, Repeat):
        for child in step.steps:
            _collect_step_point_dependencies(child, points)


def _collect_target_point_dependencies(target, points: list[str]) -> None:
    """收集点击目标中的命名点位依赖。"""
    if isinstance(target, PointRef):
        points.append(target.name)
        return
    if isinstance(target, OffsetTarget):
        _collect_target_point_dependencies(target.base, points)


def _collect_image_dependencies(
    steps: tuple[Step, ...],
    *,
    resources: TargetCatalog,
) -> tuple[str, ...]:
    """按脚本阅读顺序收集可直接传给 dry-run 的图片模板路径。"""
    images: list[str] = []
    for image in _collect_image_sources(steps):
        try:
            images.append(_resolve_image_dependency_template(image, resources=resources).path)
        except LookupError:
            continue
    return tuple(dict.fromkeys(images))


def _collect_image_sources(steps: tuple[Step, ...]) -> tuple[ImageDependencySource, ...]:
    """按步骤顺序收集图片引用，供预检查、共享资源装配与详情复用。"""
    images: list[ImageDependencySource] = []
    for step in steps:
        _collect_step_image_sources(step, images)
    return tuple(dict.fromkeys(images))


def _collect_step_image_sources(step: Step, images: list[ImageDependencySource]) -> None:
    """收集单个步骤及其全部分支中的图片引用。"""
    if isinstance(step, Click):
        target = step.point
        while isinstance(target, OffsetTarget):
            target = target.base
        if isinstance(target, ImageTarget):
            images.append(target.template)
        return
    if isinstance(step, If):
        if isinstance(step.condition, ImageExists):
            images.append(step.condition.template)
        for child in (*step.then_steps, *step.else_steps):
            _collect_step_image_sources(child, images)
        return
    if isinstance(step, Repeat):
        if isinstance(step.break_if, ImageExists):
            images.append(step.break_if.template)
        for child in step.steps:
            _collect_step_image_sources(child, images)
        return
    if isinstance(step, WaitUntil) and isinstance(step.condition, ImageExists):
        images.append(step.condition.template)


@dataclass(frozen=True, slots=True)
class _ImageReadinessDependency:
    label: str
    template: ImageTemplate | None
    source_kind: str = "direct"


def _collect_image_readiness_dependencies(
    steps: tuple[Step, ...],
    *,
    resources: TargetCatalog,
) -> tuple[_ImageReadinessDependency, ...]:
    """按脚本阅读顺序收集图片依赖检查项。"""
    return tuple(dict.fromkeys(
        _image_readiness_dependency(image, resources=resources)
        for image in _collect_image_sources(steps)
    ))


def _image_readiness_dependency(
    image: ImageDependencySource,
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
                source_kind="named_image",
            )
        except UnknownImageNameError:
            return _ImageReadinessDependency(
                label=label,
                template=None,
                source_kind="named_image",
            )
    if isinstance(image, ImageSearchSpec | SearchRef):
        try:
            return _ImageReadinessDependency(
                label=label,
                template=resources.resolve_search(image).image,
                source_kind="named_search" if isinstance(image, SearchRef) else "image_search",
            )
        except UnknownImageSearchNameError:
            return _ImageReadinessDependency(
                label=label,
                template=None,
                source_kind="missing_search",
            )
        except UnknownImageNameError:
            return _ImageReadinessDependency(
                label=label,
                template=None,
                source_kind="missing_search_image",
            )
        except UnknownRegionNameError:
            return _ImageReadinessDependency(
                label=label, template=None, source_kind="missing_search_region",
            )
    return _ImageReadinessDependency(label=label, template=image)


def _resolve_image_dependency_template(
    image: ImageDependencySource,
    *,
    resources: TargetCatalog,
) -> ImageTemplate:
    """把图片依赖解析成最终模板路径。"""
    if isinstance(image, ImageSearchSpec | SearchRef):
        return resources.resolve_search(image).image
    return resources.resolve_image(image)


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
        return dependency.label, "missing", _missing_image_dependency_message(dependency)
    image_path = Path(dependency.template.path)
    if image_path.is_absolute():
        candidate = image_path.resolve()
    elif image_path.parts[:1] == (asset_root.name,) and ".." not in image_path.parts:
        candidate = (asset_root.parent / image_path).resolve()
    else:
        return dependency.label, "unknown", "图片不在项目 assets 目录，无法确认"
    resolved_asset_root = asset_root.resolve()
    try:
        candidate.relative_to(resolved_asset_root)
    except ValueError:
        return dependency.label, "unknown", "图片不在项目 assets 目录，无法确认"
    if candidate.is_file() and candidate.suffix.lower() in supported_image_suffixes:
        if dependency.source_kind == "named_image":
            return dependency.label, "ok", f"命名图片已配置，图片文件可用：{dependency.template.path}"
        if dependency.source_kind == "named_search":
            return dependency.label, "ok", f"命名搜索已配置，图片文件可用：{dependency.template.path}"
        return dependency.label, "ok", "图片文件可用"
    if dependency.source_kind == "named_image":
        return dependency.label, "missing", f"命名图片已配置，但图片文件不存在或后缀不受支持：{dependency.template.path}"
    if dependency.source_kind == "named_search":
        return dependency.label, "missing", f"命名搜索已配置，但图片文件不存在或后缀不受支持：{dependency.template.path}"
    return dependency.label, "missing", "图片文件不存在或后缀不受支持"


def _missing_image_dependency_message(dependency: _ImageReadinessDependency) -> str:
    """生成命名图片或命名搜索无法解析时的说明。"""
    if dependency.source_kind == "missing_search":
        return "命名搜索未配置"
    if dependency.source_kind == "missing_search_image":
        return "命名搜索引用的命名图片未配置"
    if dependency.source_kind == "missing_search_region":
        return "命名搜索引用的区域未配置"
    return "命名图片未配置"


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
        _collect_condition_dependencies(step.break_if, dependencies)
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


def _describe_image(image: ImageDependencySource) -> str:
    """把图片模板、图片引用或搜索引用转换成摘要文本。"""
    if isinstance(image, ImageRef):
        return f'ImageRef("{image.name}")'
    if isinstance(image, SearchRef):
        return f'SearchRef("{image.name}")'
    if isinstance(image, ImageSearchSpec):
        return f"ImageSearchSpec({_describe_image(image.image)})"
    return image.path
