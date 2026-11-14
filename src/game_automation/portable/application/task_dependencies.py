"""静态分析任务资源引用、运行前校验和详情依赖。

本 module 消费统一任务事实，判断共享资源需求并生成 readiness。
它不生成步骤摘要、不运行任务，也不处理 UI 展示细节。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.domain import (
    ImageRef,
    ImageTemplate,
    PointRef,
    SearchRef,
    TargetCatalog,
)
from game_automation.portable.domain.point_aliases import (
    UnknownImageNameError,
    UnknownImageSearchNameError,
    UnknownPointNameError,
    UnknownRegionNameError,
)
from game_automation.portable.domain.task import FunctionTask
from game_automation.portable.domain.task_analysis import (
    ImageDependencySource,
    TaskAnalysis,
    TaskDependency,
    analyze_task,
)


@dataclass(frozen=True, slots=True)
class TaskDependencyDetails:
    dependencies: tuple[str, ...] = ()
    state_dependencies: tuple[str, ...] = ()
    point_dependencies: tuple[str, ...] = ()
    image_dependencies: tuple[str, ...] = ()
    readiness: tuple[tuple[str, str, str], ...] = ()


def validate_task_resource_references(task: FunctionTask) -> None:
    """执行前解析任务声明的资源引用，不读取桌面或要求模拟模板文件存在。"""
    analysis = analyze_task(task)
    for name in analysis.point_names:
        task.resources.resolve_point(PointRef(name))
    for image in analysis.image_sources:
        _resolve_image_dependency_template(image, resources=task.resources)


def task_needs_shared_resources(task: FunctionTask) -> bool:
    """仅在任务引用的搜索或区域无法由局部资源解析时请求共享配置。"""
    analysis = analyze_task(task)
    for image in analysis.image_sources:
        if isinstance(image, SearchRef):
            try:
                task.resources.resolve_search(image)
            except UnknownImageSearchNameError, UnknownRegionNameError:
                return True
            except UnknownImageNameError:
                # 状态配置不提供命名图片，缺失的局部图片由预检查报告。
                continue
    return False


def describe_task_dependencies(
    task: FunctionTask,
    *,
    asset_root: Path,
    supported_image_suffixes: frozenset[str],
    state_names: tuple[str, ...] | None,
    analysis: TaskAnalysis | None = None,
) -> TaskDependencyDetails:
    """生成任务依赖摘要、结构化依赖和运行前检查。"""
    analysis = analysis if analysis is not None else analyze_task(task)
    point_names = analysis.point_names
    image_sources = analysis.image_sources
    dependencies = tuple(
        dict.fromkeys(
            (
                *(f"状态: {name}" for name in analysis.state_names),
                *(_describe_reference(ref) for ref in analysis.references),
                *(("颜色读取",) if analysis.uses_colors else ()),
            )
        )
    )
    return TaskDependencyDetails(
        dependencies=dependencies,
        state_dependencies=analysis.state_names,
        point_dependencies=point_names,
        image_dependencies=_resolved_image_paths(
            image_sources, resources=task.resources
        ),
        readiness=_describe_readiness(
            analysis=analysis,
            resources=task.resources,
            asset_root=asset_root,
            supported_image_suffixes=supported_image_suffixes,
            state_names=state_names,
        ),
    )


def _describe_readiness(
    *,
    analysis: TaskAnalysis,
    resources: TargetCatalog,
    asset_root: Path,
    supported_image_suffixes: frozenset[str],
    state_names: tuple[str, ...] | None,
) -> tuple[tuple[str, str, str], ...]:
    """生成任务详情中的运行前依赖检查结果。"""
    checks = []
    for name in analysis.state_names:
        checks.append(_screen_state_readiness(name, state_names=state_names))
    for name in analysis.point_names:
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
        for dependency in dict.fromkeys(
            _image_readiness_dependency(image, resources=resources)
            for image in analysis.image_sources
        )
    )
    return tuple(dict.fromkeys(checks))


def _resolved_image_paths(
    image_sources: tuple[ImageDependencySource, ...],
    *,
    resources: TargetCatalog,
) -> tuple[str, ...]:
    """按脚本阅读顺序收集可直接传给 dry-run 的图片模板路径。"""
    images: list[str] = []
    for image in image_sources:
        try:
            images.append(
                _resolve_image_dependency_template(image, resources=resources).path
            )
        except LookupError:
            continue
    return tuple(dict.fromkeys(images))


@dataclass(frozen=True, slots=True)
class _ImageReadinessDependency:
    label: str
    template: ImageTemplate | None
    source_kind: str


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
    try:
        return _ImageReadinessDependency(
            label=label,
            template=resources.resolve_search(image).image,
            source_kind="named_search",
        )
    except UnknownImageSearchNameError:
        return _ImageReadinessDependency(label, None, "missing_search")
    except UnknownImageNameError:
        return _ImageReadinessDependency(label, None, "missing_search_image")
    except UnknownRegionNameError:
        return _ImageReadinessDependency(label, None, "missing_search_region")


def _resolve_image_dependency_template(
    image: ImageDependencySource,
    *,
    resources: TargetCatalog,
) -> ImageTemplate:
    """把图片依赖解析成最终模板路径。"""
    if isinstance(image, SearchRef):
        return resources.resolve_search(image).image
    return resources.resolve_image(image)


def _screen_state_readiness(
    state: str,
    *,
    state_names: tuple[str, ...] | None,
) -> tuple[str, str, str]:
    """检查任务引用的界面状态是否能从窗口规则中确认。"""
    dependency = f"状态: {state}"
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
    """检查任务引用的 assets 图片是否存在。"""
    if dependency.template is None:
        return (
            dependency.label,
            "missing",
            _missing_image_dependency_message(dependency),
        )
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
            return (
                dependency.label,
                "ok",
                f"命名图片已配置，图片文件可用：{dependency.template.path}",
            )
        return (
            dependency.label,
            "ok",
            f"命名搜索已配置，图片文件可用：{dependency.template.path}",
        )
    if dependency.source_kind == "named_image":
        return (
            dependency.label,
            "missing",
            f"命名图片已配置，但图片文件不存在或后缀不受支持：{dependency.template.path}",
        )
    return (
        dependency.label,
        "missing",
        f"命名搜索已配置，但图片文件不存在或后缀不受支持：{dependency.template.path}",
    )


def _missing_image_dependency_message(dependency: _ImageReadinessDependency) -> str:
    """生成命名图片或命名搜索无法解析时的说明。"""
    if dependency.source_kind == "missing_search":
        return "命名搜索未配置"
    if dependency.source_kind == "missing_search_image":
        return "命名搜索引用的命名图片未配置"
    if dependency.source_kind == "missing_search_region":
        return "命名搜索引用的区域未配置"
    return "命名图片未配置"


def _describe_image(image: ImageDependencySource) -> str:
    """把声明中的图片或搜索引用转换成摘要文本。"""
    if isinstance(image, ImageRef):
        return f'ImageRef("{image.name}")'
    return f'SearchRef("{image.name}")'


def _describe_reference(reference: TaskDependency) -> str:
    """把共同分析中的依赖事实转成用户可见标签。"""
    if isinstance(reference, PointRef):
        return f"点位: {reference.name}"
    return f"图片: {_describe_image(reference)}"
