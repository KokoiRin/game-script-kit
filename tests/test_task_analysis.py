"""验证函数任务声明驱动详情、资源检查及端口装配的一致性。

本模块只读源码和临时素材，不解释 Python 流程或访问桌面。
"""

import pytest

from game_automation.portable.application.task_dependencies import (
    describe_task_dependencies,
    task_needs_shared_resources,
    validate_task_resource_references,
)
from game_automation.portable.application.task_resources import (
    task_with_shared_resources,
)
from game_automation.portable.domain import (
    ImageRef,
    ImageSearchSpec,
    ImageTemplate,
    NamedRegion,
    PointRef,
    Rect,
    RegionRef,
    SearchRef,
    TargetCatalog,
)
from game_automation.portable.domain.task import FunctionTask, TaskRequirements
from game_automation.portable.domain.task_analysis import analyze_task
from game_automation.portable.engine.runtime_requirements import (
    inspect_runtime_requirements,
)
from tests.support.function_tasks import function_task


def test_analysis_preserves_declared_order_and_deduplicates_names(tmp_path):
    """资源事实按声明分组稳定去重，状态和取色需求独立保留。"""
    task = FunctionTask(
        "declarations",
        tmp_path / "task.py",
        "def run(ctx): pass",
        requires=TaskRequirements(
            points=("open", "open"),
            images=("button", "button"),
            searches=("confirm",),
            states=("home", "done", "home"),
            colors=True,
        ),
    )

    analysis = analyze_task(task)
    requirements = inspect_runtime_requirements(task)

    assert analysis.references == (
        PointRef("open"),
        ImageRef("button"),
        SearchRef("confirm"),
    )
    assert analysis.point_names == ("open",)
    assert analysis.image_sources == (ImageRef("button"), SearchRef("confirm"))
    assert analysis.state_names == ("home", "done")
    assert analysis.uses_colors
    assert requirements.needs_color_reader
    assert requirements.needs_image_locator
    assert requirements.needs_screen_state_reader


def test_declared_search_region_missing_shared_resource_is_reported_then_resolved(
    tmp_path,
):
    """共享区域的缺失事实同时驱动详情、按需装配与运行前检查。"""
    image = ImageTemplate(str(tmp_path / "button.png"))
    (tmp_path / "button.png").write_bytes(b"template")
    from game_automation.portable.domain import NamedImageSearch

    resources = TargetCatalog(
        searches=(
            NamedImageSearch("button", ImageSearchSpec(image, RegionRef("dialog"))),
        )
    )
    task = function_task("search", 'ctx.click_image("button")', resources=resources)

    before = describe_task_dependencies(
        task,
        asset_root=tmp_path,
        supported_image_suffixes=frozenset({".png"}),
        state_names=(),
    )

    assert task_needs_shared_resources(task)
    assert before.readiness[0][1] == "missing"
    with pytest.raises(LookupError, match="dialog"):
        validate_task_resource_references(task)
    prepared = task_with_shared_resources(
        task, TargetCatalog(regions=(NamedRegion("dialog", Rect(0, 0, 20, 30)),))
    )
    after = describe_task_dependencies(
        prepared,
        asset_root=tmp_path,
        supported_image_suffixes=frozenset({".png"}),
        state_names=(),
    )
    assert not task_needs_shared_resources(prepared)
    assert after.image_dependencies == (image.path,)
    assert after.readiness[0][1] == "ok"
    assert str(image.path) in after.readiness[0][2]
    validate_task_resource_references(prepared)
